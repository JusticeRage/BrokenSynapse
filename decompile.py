from __future__ import print_function
import sys
import os
import copy
import bisect

from torque_vm_values import *


def pretty_print_function(function_name, namespace="", arguments=None, call_type="FunctionCall"):
    if arguments is None:
        arguments = []

    # Sanitize arguments. Their name may be omitted if they are unused.
    for i in range(0, len(arguments)):
        if not arguments[i]:
            arguments[i] = "%%unused_var_%d" % i

    function_call = "%s::" % namespace if namespace != "" else ""
    if call_type == "MethodCall":
        if " " in arguments[0]:  # The caller name may have been constructed dynamically, i.e. (Objh @ "andle").call()
            function_call += "(%s)." % arguments[0]
        else:
            function_call += "%s." % arguments[0]
        arguments = arguments[1:]
    function_call += "%s(" % function_name
    if len(arguments) == 0:
        function_call += ")"
    else:
        for arg in arguments:
            function_call += "%s, " % arg if arg is not arguments[-1] else "%s)" % arg
    return function_call


def is_number(s):
    """
    Checks whether the contents of a string are actually a number.
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def partial_decompile(dso, start, end, in_function, previous_offset=0):
    dso_copy = copy.copy(dso)
    assert(start < end)
    dso_copy.code = dso.code[start:end]  # Stop just before the comparison opcode
    with open(os.devnull, 'w') as f:
        return decompile(dso_copy, sink=f, in_function=in_function, offset=start + previous_offset)
        
def get_jmp_target(dso, jmp, code_inserts, offset):
    """
    Finds original jump target and returns the position of the earliest metadata before it or itself 
    if there is none. This is useful for finding code at a relative position left of the jump target
    @param  dso          The object in which the jump was found
    @param  jmp          Index of parameter to jump, jmp - 1 contains the opcode with a jump
    @param  code_inserts Sorted list with indexes of where code is currently inserted
    @param  offset       An offset to apply to absolute jumps.
    """
    jmp_target = dso.code[jmp] - offset
    for i in range(len(code_inserts)):
        if (jmp_target <= code_inserts[i]):
            break
        jmp_target += 1
    return jmp_target
        
def insert_code(dso, code_inserts, index, value):
    dso.code.insert(index, value)
    for i in range(bisect.bisect_left(code_inserts, index), len(code_inserts)):
        code_inserts[i] += 1
    bisect.insort(code_inserts, index)

def delete_code(dso, code_inserts, index):
    del dso.code[index]
    assert code_inserts[bisect.bisect_left(code_inserts, index)] == index
    del code_inserts[bisect.bisect_left(code_inserts, index)]
    for i in range(bisect.bisect_left(code_inserts, index), len(code_inserts)):
        code_inserts[i] -= 1

def decompile(dso, sink=None, in_function=False, offset=0):
    """
    Decompiles the DSO object given as parameter.
    @param  dso         The object to decompile
    @param  sink        A file object in which the decompiled code will be written. Default is stdout.
    @param  in_function Whether the code to decompile is located in a function.
                        Do not use. It is only relevant to partial decompilations.
    @param  offset      An offset to apply to absolute jumps.
                        Do not use. It is only relevant to partial decompilations.
    """
    if dso.version < 44:
        ste_size = 1
    else:
        # StringTable entries were "expanded to 64bits" in this version. Some sizes vary accordingly.
        ste_size = 2

    ip = 0
    string_stack = []
    int_stack = []
    float_stack = []
    arguments = []
    binary_stack = []  # No counterpart in the VM. Used to keep track of binary operations.
    object_creation_stack = []
    current_variable = None
    current_field = None
    current_object = None
    indentation = 0
    previous_opcodes = ["OP_INVALID", "OP_INVALID", "OP_INVALID", "OP_INVALID", "OP_INVALID"]
    code_inserts = []
    
    # For debugging
    # for i in range(len(dso.code)):
    #     print("Opcode: %s\nValue: %s\nIp: %s\n" % (get_opcode(dso.version, dso.code[i]), hex(dso.code[i]), hex(i)), file=sys.stderr)

    # The big switch-case
    while ip < len(dso.code):
        opcode = get_opcode(dso.version, dso.code[ip])
        # For debugging
        # print("Opcode: %s\nValue: %s\nIp: %s\n" % (opcode, hex(dso.code[ip]), hex(ip)), file=sys.stdout)
        if not opcode:
            raise ValueError("Encountered a value which does not translate to an opcode (%d)." % dso.code[ip])
        ip += 1

        if opcode == "OP_DOCBLOCK_STR":
            print(indentation*"\t" + "///%s" % dso.get_string(dso.code[ip], in_function), file=sink)
            ip += 1
        elif opcode == "OP_LOADIMMED_STR" or opcode == "OP_TAG_TO_STR":
            op = dso.get_string(dso.code[ip], in_function)
            ip += 1
            # Some floats may be represented as string literals. Omit brackets for those.
            if opcode == "OP_TAG_TO_STR":  # Tagged strings are encased in single quotes.
                string_stack.append('%s' % op if is_number(op) else "'%s'" % op)
            else:
                # Also escape any double quote in the string.
                string_stack.append('%s' % op if is_number(op) else '"%s"' % op.replace('"', r'\"'))
        elif opcode == "OP_SETCURVAR_CREATE" or opcode == "OP_SETCURVAR":
            current_variable = dso.get_string(dso.code[ip])  # Always lookup in the global ST for this opcode
            ip += ste_size
        elif  opcode == "OP_SETCURVAR_ARRAY_CREATE" or opcode == "OP_SETCURVAR_ARRAY":
            current_variable = string_stack.pop()
        elif opcode == "OP_SAVEVAR_STR":
            print(indentation*"\t" + '%s = %s;' % (current_variable, string_stack[-1]), file=sink)
        elif opcode == "OP_STR_TO_NONE":
            if previous_opcodes[0] == "OP_CALLFUNC" or previous_opcodes[0] == "OP_CALLFUNC_RESOLVE":
                # CALLFUNC -> STR_TO_NONE means ignored return value. Write the call right now, because
                # it won't be assigned to anything.
                print("%s%s;" % (indentation*"\t", string_stack.pop()), file=sink)
            else:
                try:
                    string_stack.pop()  # I get some mismatches with the OP_TERMINATE_REWIND_STR opcode family.
                except IndexError:
                    pass

        elif opcode == "OP_STR_TO_FLT":
            float_stack.append(string_stack.pop())
        elif opcode == "OP_STR_TO_UINT":
            int_stack.append(string_stack.pop())
        elif opcode == "OP_LOADVAR_STR":
            string_stack.append(current_variable)
            # We're happy to keep the name.
        elif opcode == "OP_LOADVAR_FLT":
            float_stack.append(current_variable)
            # We're happy to keep the name.
        elif opcode == "OP_LOADVAR_UINT":
            int_stack.append(current_variable)
        elif opcode == "OP_LOADIMMED_UINT":
            int_stack.append(dso.code[ip])
            ip += 1
        elif opcode == "OP_SAVEVAR_UINT":
            print(indentation*"\t" + "%s = %s;" % (current_variable, int_stack[-1]), file=sink)
        elif opcode == "OP_UINT_TO_NONE":
            done_object_opcode = ""
            if dso.version < 45:
                done_object_opcode = "OP_END_OBJECT"
            else:
                done_object_opcode = "OP_FINISH_OBJECT"
            
            if previous_opcodes[0] == done_object_opcode:
                print(indentation*"\t" + int_stack.pop(), file=sink)
            else:
                int_stack.pop()
        elif opcode == "OP_UINT_TO_FLT":
            float_stack.append(int_stack.pop())
        elif opcode == "OP_LOADIMMED_FLT":
            pos = dso.code[ip]
            ip += 1
            float_stack.append(dso.get_float(pos, in_function))
        elif opcode == "OP_SAVEVAR_FLT":
            print(indentation*"\t" + '%s = %s;' % (current_variable, str(float_stack[-1])), file=sink)
        elif opcode == "OP_FLT_TO_UINT":
            int_stack.append(float_stack.pop())
        elif opcode == "OP_FLT_TO_NONE":
            float_stack.pop()
        elif opcode == "OP_LOADIMMED_IDENT":
            string_stack.append('%s' % dso.get_string(dso.code[ip]))  # Always pick from the global pool
            ip += ste_size
        elif opcode == "OP_PUSH_FRAME":
            # Create a new "argument" frame.
            arguments.append([])
            pass
        elif opcode == "OP_PUSH":
            if dso.version <= 36:
                if len(arguments) == 0:
                    arguments.append([])  # Old versions don't seem to push stack frames all the time.
            arguments[-1].append(string_stack.pop())
        elif opcode == "OP_CALLFUNC_RESOLVE" or opcode == "OP_CALLFUNC":
            namespace_offset = dso.code[ip+ste_size]
            call_type = CALL_TYPES[dso.code[ip+2*ste_size]]
            if namespace_offset:
                namespace = dso.get_string(namespace_offset)
            else:
                namespace = ""
            function_name = dso.get_string(dso.code[ip])
            string_stack.append(pretty_print_function(function_name, namespace, arguments[-1], call_type))
            arguments.pop()
            ip += 1 + 2*ste_size

        elif opcode == "OP_FUNC_DECL":
            function_name = dso.get_string(dso.code[ip])
            if dso.code[ip + ste_size] == 0:
                namespace = ""
            else:
                namespace = dso.get_string(dso.code[ip + ste_size])
            package = dso.get_string(dso.code[ip + 2*ste_size])
            has_body = dso.code[ip + 3*ste_size]
            end_ip = dso.code[ip + 3*ste_size + 1]
            # Mark the end of the function so we can close the bracket and unindent.
            # We can't rely on "return" because a function may have multiple exit points.
            insert_code(dso, code_inserts, end_ip, METADATA["META_ENDFUNC"])
            argc = dso.code[ip + 3*ste_size + 2]
            argv = []
            for i in range(0, argc):
                argv.append(dso.get_string(dso.code[ip + 3*ste_size + 3 + ste_size*i]))

            print(indentation*"\t" + "function " + pretty_print_function(function_name, namespace, argv) + "\n{", file=sink)
            indentation += 1
            ip += 3 + 3*ste_size + ste_size*argc
            in_function = True
        elif opcode == "OP_RETURN":
            if len(string_stack) > 0:
                print(indentation*"\t" + "return %s;" % string_stack.pop(), file=sink)
            elif ip != len(dso.code) and dso.code[ip] != METADATA["META_ENDFUNC"]:
                # Omit the return if the function or the script ends here
                print(indentation*"\t" + "return;", file=sink)
        elif opcode == "OP_RETURN_VOID":
            if ip != len(dso.code) and dso.code[ip] != METADATA["META_ENDFUNC"]:
                # Omit the return if the function or the script ends here
                print(indentation*"\t" + "return;", file=sink)
        elif opcode == "META_ENDFUNC":
            if in_function:
                in_function = False
                indentation -= 1
                print(indentation*"\t" + "}\n", file=sink)
            delete_code(dso, code_inserts, ip - 1)  # Delete the metadata we added to avoid desyncing absolute jumps.
            ip -= 1
        elif opcode == "OP_CREATE_OBJECT":
            #  A 0 has been pushed to the int stack because it will contain a handle to the object.
            # Replace that 0 with the code of the object creation.
            parent = dso.get_string(dso.code[ip])
            if parent != "":
                pass  # TODO!
            argv = arguments[-1]
            object_creation = "new %s(%s)\n" % (argv[0], argv[1] if argv[1] != "\"\"" else "")
            object_creation += indentation*"\t" + "{\n"
            if dso.version < 45:
                assert int_stack.pop() == 0
                int_stack.append(object_creation)
            else:
                object_creation_stack.append(object_creation)
            indentation += 1
            arguments.pop()
            # Structure: parent (size = 1 or 2), isDataBlock, isInternal, isSingleton, lineNumber, failjump.
            ip += 5 + ste_size
            if dso.version < 45:
                ip -= 1 # Older versions don't have a byte for lineNumber
        elif opcode == "OP_ADD_OBJECT":
            if dso.version < 45:
                pass
            else:
                root = dso.code[ip]
                if root:
                    assert int_stack.pop() == 0
                int_stack.append(object_creation_stack.pop())
            ip += 1
        elif opcode == "OP_END_OBJECT":
            indentation -= 1
            op = int_stack.pop()
            if op.endswith("\n" + indentation*"\t" + "{\n"):  # Empty object declaration, omit body.
                op = op[:-3-indentation]
            else:
                op += indentation*"\t" + "}"
            if dso.version < 45:
                int_stack.append(op)
            else:
                root = dso.code[ip]
                if root:
                    int_stack.append(op)
                else:
                    int_stack.append(int_stack.pop() + indentation*"\t" + op + "\n")
            ip += 1
        elif opcode == "OP_FINISH_OBJECT":
            pass
        elif opcode == "OP_ADVANCE_STR":
            pass
        elif opcode == "OP_ADVANCE_STR_NUL":
            pass
        elif opcode == "OP_ADVANCE_STR_APPENDCHAR":
            c = chr(dso.code[ip])
            string_stack[-1] += c
            ip += 1
        elif opcode == "OP_ADVANCE_STR_COMMA":
            string_stack[-1] += ","
        elif opcode == "OP_SETCUROBJECT":
            current_object = string_stack.pop()
        elif opcode == "OP_SETCUROBJECT_NEW":
            current_object = None
        elif opcode == "OP_SETCUROBJECT_INTERNAL":
            ip += 1
            current_object = string_stack.pop()
            int_stack.append(current_object)
        elif opcode == "OP_SETCURFIELD":
            current_field = dso.get_string(dso.code[ip])
            ip += ste_size
        elif opcode == "OP_SETCURFIELD_ARRAY":
            pass
        elif opcode == "OP_REWIND_STR":
            if ip < len(dso.code) and get_opcode(dso.version, dso.code[ip]).startswith("OP_SETCURVAR_ARRAY"):  # This is an array access
                s2 = string_stack.pop()
                string_stack.append("%s[%s]" % (string_stack.pop(), s2))
            else:
                s2 = string_stack.pop()
                s1 = string_stack.pop()
                if s1[-1] in STRING_OPERATORS:
                    string_stack.append("%s %s %s" % (s1[:-1], STRING_OPERATORS[s1[-1]], s2))
                elif s1[-1] == ",":  # Matrix indexing
                    string_stack.append("%s%s" % (s1, s2))
                else:
                    string_stack.append("%s @ %s" % (s1, s2))
        elif opcode == "OP_LOADFIELD_FLT":
            float_stack.append("%s.%s" % (current_object, current_field))
        elif opcode == "OP_LOADFIELD_STR":
            string_stack.append("%s.%s" % (current_object, current_field))
        elif opcode == "OP_LOADFIELD_UINT":
            int_stack.append("%s.%s" % (current_object, current_field))
        elif opcode == "OP_TERMINATE_REWIND_STR":
            pass
        elif opcode == "OP_SAVEFIELD_STR":
            if dso.version <= 36 and len(string_stack) == 0:
                string_stack.append("\"\"")
            if current_object is None:  # This is an object creation
                if dso.version < 45:
                    int_stack[-1] += indentation*"\t" + "%s = %s;\n" % (current_field, string_stack[-1])
                else:
                    object_creation_stack[-1] += indentation*"\t" + "%s = %s;\n" % (current_field, string_stack[-1])
            else:  # This is a field affectation
                print(indentation*"\t" + "%s.%s = %s;" % (current_object, current_field, string_stack[-1]), file=sink)
        elif opcode == "OP_SAVEFIELD_FLT":
            if current_object is None:  # This is an object creation
                if dso.version < 45:
                    int_stack[-1] += indentation*"\t" + "%s = %s;\n" % (current_field, float_stack.pop())
                else:
                    object_creation_stack[-1] += indentation*"\t" + "%s = %s;\n" % (current_field, float_stack.pop())
            else:  # This is a field affectation
                print(indentation*"\t" + "%s.%s = %s;" % (current_object, current_field, float_stack[-1]), file=sink)
        elif opcode == "OP_CMPEQ" or \
             opcode == "OP_CMPLT" or \
             opcode == "OP_CMPNE" or \
             opcode == "OP_CMPGR" or \
             opcode == "OP_CMPGE" or \
             opcode == "OP_CMPLE":
            op1 = float_stack.pop()
            op2 = float_stack.pop()
            op1 = "%s %s %s" % (str(op1), COMPARISON[opcode], str(op2))
            int_stack.append(op1)
        elif opcode == "OP_JMP":
            jmp_target = get_jmp_target(dso, ip, code_inserts, offset)
            opcode_before_dest = get_opcode(dso.version, dso.code[jmp_target - 2])
            if opcode_before_dest == "META_ENDWHILE" or opcode_before_dest == "META_ENDWHILE_FLT" or opcode_before_dest == "OP_ITER_END":
                # Jumping after the end of a while loop means the "break" keyword was used
                print(indentation*"\t" + "break;", file=sink)
            elif get_opcode(dso.version, dso.code[ip + 1]) == "OP_ITER_END":
                # Jumping right before the end of a foreach loop means no keyword was used
                pass
            else:
                # We should probably have some assert here that checks for the start of a loop but I'm pretty sure the only other case is for the "continue" keyword
                print(indentation*"\t" + "continue;", file=sink)
            ip += 1
        elif opcode == "OP_JMPIF_NP":
            binary_stack.append(str(int_stack.pop()) + " || ")
            jmp_target = get_jmp_target(dso, ip, code_inserts, offset)
            insert_code(dso, code_inserts, jmp_target, METADATA["META_END_BINARYOP"])
            ip += 1
        elif opcode == "OP_JMPIFNOT_NP":
            binary_stack.append(str(int_stack.pop()) + " && ")
            jmp_target = get_jmp_target(dso, ip, code_inserts, offset)
            insert_code(dso, code_inserts, jmp_target, METADATA["META_END_BINARYOP"])
            ip += 1
        elif opcode == "META_END_BINARYOP":
            delete_code(dso, code_inserts, ip - 1)  # Delete the metadata we added to avoid desyncing absolute jumps.
            ip -= 1
            op1 = binary_stack.pop()
            op2 = str(int_stack.pop())
            if "&&" in op2 or "||" in op2:
                op2 = "(%s)" % op2
            int_stack.append("%s%s" % (op1, op2))
        elif opcode == "OP_JMPIFNOT" or opcode == "OP_JMPIFFNOT":
            # We need to determine the type of branch we're facing. The opcode just before the jump destination
            # gives us hints.
            jmp_target = get_jmp_target(dso, ip, code_inserts, offset)
            if jmp_target < ip:
                print("Error: unexpected backward jump.", file=sys.stderr)
                sys.exit(1)
            elif jmp_target == ip + 1:  # If statement with an empty body. Simply skip it.
                ip += 1
                if opcode == "OP_JMPIFNOT":
                    int_stack.pop()
                elif opcode == "OP_JMPIFFNOT":
                    float_stack.pop()
                continue
            opcode_before_dest = get_opcode(dso.version, dso.code[jmp_target - 2])
            # Probably ambiguous :(
            if opcode_before_dest == "OP_JMP":  # If-then-else construction or ternary operator
                # Test if this is a ternary expression, i.e (a ? b : c)
                opcode_before_jmp = get_opcode(dso.version, dso.code[jmp_target - 4])
                if opcode_before_jmp and opcode_before_jmp.startswith("OP_LOAD"):
                    # The loop ends with something being pushed on a stack. This is a ternary operator.
                    dso.code[jmp_target - 2] = METADATA["META_ELSE"]
                    # Obtain the stacks after evaluating the expression:
                    try:
                        s_s, i_s, f_s = partial_decompile(dso, ip+1, dso.code[jmp_target - 1], in_function, offset)
                        if len(s_s) == 2:
                            op1 = s_s.pop()
                            string_stack.append("(%s) ? %s : %s" % (int_stack.pop() if opcode == "OP_JMPIFNOT" else float_stack.pop(),
                                                                  s_s.pop(),
                                                                  op1))
                            ip = dso.code[jmp_target - 1] # Skip past the construction
                            continue
                        elif len(i_s) == 2:
                            op1 = i_s.pop()
                            int_stack.append("(%s) ? %s : %s" % (int_stack.pop() if opcode == "OP_JMPIFNOT" else float_stack.pop(),
                                                               i_s.pop(),
                                                               op1))
                            ip = dso.code[jmp_target - 1]
                            continue
                        elif len(f_s) == 2:
                            op1 = f_s.pop()
                            float_stack.append("(%s) ? %s : %s" % (int_stack.pop() if opcode == "OP_JMPIFNOT" else float_stack.pop(),
                                                                 f_s.pop(),
                                                                 op1))
                            ip = dso.code[jmp_target - 1]
                            continue
                    except:
                        pass
                    # If this point is reached, this may not have been a ternary operator after all.
                dest_jmp_target = get_jmp_target(dso, jmp_target - 1, code_inserts, offset)
                opcode_before_dest_jmp_dest = get_opcode(dso.version, dso.code[dest_jmp_target - 2])
                jmp_break = opcode_before_dest_jmp_dest == "META_ENDWHILE" or opcode_before_dest_jmp_dest == "META_ENDWHILE_FLT" or opcode_before_dest_jmp_dest == "OP_ITER_END"
                jmp_continue = False #TODO
                if not jmp_break:
                    # If opcode_before_dest jump is not a break or continue, the jump is to skip past an else
                    # If-then-else
                    if opcode == "OP_JMPIFNOT":
                        print(indentation*"\t" + "if (%s)" % int_stack.pop() + "\n" + indentation*"\t" + "{", file=sink)
                    elif opcode == "OP_JMPIFFNOT":
                        print(indentation*"\t" + "if (%s)" % float_stack.pop() + "\n" + indentation*"\t" + "{", file=sink)
                    # Annotate code
                    dso.code[jmp_target - 2] = METADATA["META_ELSE"]
                    insert_code(dso, code_inserts, dest_jmp_target, METADATA["META_ENDIF"])
                    ip += 1
                    indentation += 1
                    continue
            elif (opcode_before_dest == "OP_JMPIFNOT" or opcode_before_dest == "OP_JMPIF" or opcode_before_dest == "OP_JMPIFF") and \
                 dso.code[jmp_target - 1] - offset == ip + 1:  # For/While loop
                ind = indentation*"\t"
                # This may be an easy while loop:
                if opcode == "OP_JMPIFNOT":
                    print(ind + "while(%s)\n" % int_stack.pop() + ind + "{", file=sink)
                elif opcode == "OP_JMPIFFNOT":
                    print(ind + "while(%s)\n" % float_stack.pop() + ind + "{", file=sink)
                if opcode_before_dest == "OP_JMPIFNOT" or opcode_before_dest == "OP_JMPIF":
                    dso.code[jmp_target - 2] = METADATA["META_ENDWHILE"]
                elif opcode_before_dest == "OP_JMPIFF": 
                    dso.code[jmp_target - 2] = METADATA["META_ENDWHILE_FLT"]
                ip += 1
                indentation += 1
                continue
            # Generic opcode before the jump target. We assume that the execution is continuing and
            # that this is therefore a simple If control structure.
            if opcode == "OP_JMPIFNOT":
                print(indentation*"\t" + "if (%s)" % int_stack.pop() + "\n" + indentation*"\t" + "{", file=sink)
            elif opcode == "OP_JMPIFFNOT":
                print(indentation*"\t" + "if (%s)" % float_stack.pop() + "\n" + indentation*"\t" + "{", file=sink)
            insert_code(dso, code_inserts, jmp_target, METADATA["META_ENDIF"])
            ip += 1
            indentation += 1
        elif opcode == "OP_NOT":
            op1 = str(int_stack.pop())
            if op1.count("==") == 1:
                int_stack.append(op1.replace("==", "!="))
            elif op1.count("!=") == 1:
                int_stack.append(op1.replace("!=", "=="))
            elif op1.count("$=") == 1:
                int_stack.append(op1.replace("$=", "!$="))
            elif op1.count("!$=") == 1:
                int_stack.append(op1.replace("!$=", "$="))
            elif not op1.startswith("!"):
                int_stack.append("!%s" % op1)
            elif " " in op1:
                int_stack.append("!(%s)" % op1)  # Encase in parentheses if this is a compound operation
            else:
                int_stack.append(op1[1:])  # Avoid "!!" in front of variables
        elif opcode == "OP_NOTF":
            op1 = float_stack.pop()
            if isinstance(op1, str):
                if not op1.startswith("!"):
                    int_stack.append("!%s" % op1)
                else:
                    int_stack.append(op1[1:])  # Avoid "!!" in front of variables
            else:  # The VM replaces true and false with 0 and 1.
                int_stack.append("false" if float(op1) == 0 else "true")
        elif opcode == "OP_MUL":
            op1 = float_stack.pop()
            if isinstance(op1, str) and (' + ' in op1 or " - " in op1):
                op1 = "(%s)" % op1  # operand is the result of an add/sub, prevent priority issues.
            float_stack.append("%s * %s" % (op1, float_stack.pop()))
        elif opcode == "OP_DIV":
            op1 = float_stack.pop()
            if isinstance(op1, str) and ('+' in op1 or " -" in op1):
                op1 = "(%s)" % op1  # operand is the result of an add/sub, prevent priority issues.
            float_stack.append("%s / %s" % (op1, float_stack.pop()))
        elif opcode == "OP_ADD":
            float_stack.append("%s + %s" % (float_stack.pop(), float_stack.pop()))
        elif opcode == "OP_SUB":
            float_stack.append("%s - %s" % (float_stack.pop(), float_stack.pop()))
        elif opcode == "OP_NEG":
            op1 = float_stack.pop()
            if op1 is not str:
                float_stack.append(-1 * op1)
            else:
                if op1.startswith("-"):
                    float_stack.append(op1[1:])
                else:
                    float_stack.append("(-1 *%s)" % op1)
        elif opcode == "OP_MOD":
            op = int_stack.pop()
            int_stack.append("%s %% %s" % (int_stack.pop(), op))
        elif opcode == "OP_COMPARE_STR":
            op = string_stack.pop()
            int_stack.append("%s $= %s" % (string_stack.pop(), op))
        elif opcode == "OP_FLT_TO_STR":
            string_stack.append(str(float_stack.pop()))
        elif opcode == "OP_UINT_TO_STR":
            string_stack.append(str(int_stack.pop()))
        elif opcode == "OP_BREAK":
            pass  # Ignore breakpoints
        elif opcode == "META_ELSE":
            ind = (indentation-1)*"\t"
            print(ind + "}\n" + ind + "else\n" + ind + "{", file=sink)
            ip += 1  # META_ELSE replaces an existing opcode so there it doesn't cause problems - no need to del it
        elif opcode == "META_ENDIF" or opcode == "META_ENDWHILE_FLT" or opcode == "META_ENDWHILE" or opcode == "OP_ITER_END":
            indentation -= 1
            print(indentation*"\t" + "}", file=sink)
            if opcode == "META_ENDIF":
                delete_code(dso, code_inserts, ip - 1)  # Delete the metadata we added to avoid desyncing absolute jumps.
                ip -= 1
            elif opcode == "META_ENDWHILE_FLT":
                ip += 1
                float_stack.pop()  # A test condition will have been pushed and needs to be cleaned.
            elif opcode == "META_ENDWHILE":
                ip += 1
                int_stack.pop()  # A test condition will have been pushed and needs to be cleaned.
        elif opcode == "OP_BITOR":
            op = int_stack.pop()
            int_stack.append("%s | %s" % (int_stack.pop(), op)) # kind of winged this and it worked
        elif opcode == "OP_BITAND":
            op = int_stack.pop()
            int_stack.append("%s & %s" % (int_stack.pop(), op))
        elif opcode == "OP_SHR":
            op = int_stack.pop()
            int_stack.append("%s >> %s" % (int_stack.pop(), op))
        elif opcode == "OP_SHL":
            op = int_stack.pop()
            int_stack.append("%s << %s" % (int_stack.pop(), op))
        elif opcode == "OP_AND":
            op = int_stack.pop()
            int_stack.append("%s && %s" % (int_stack.pop(), op))
        elif opcode == "OP_OR":
            op = int_stack.pop()
            int_stack.append("%s || %s" % (int_stack.pop(), op))
        elif opcode == "OP_ASSERT":
            print(indentation*"\t" + "assert(\"%s\");" % dso.get_string(dso.code[ip], in_function), file=sink)
            ip += 1
        elif opcode == "OP_ITER_BEGIN":
            ind = indentation*"\t"
            print(ind + "foreach(%s in %s)\n" % (dso.get_string(dso.code[ip]), string_stack.pop()) + ind + "{", file=sink)
            ip += 3
            indentation += 1
        elif opcode == "OP_ITER":
            ip += 1
        else:
            print("%s not implemented yet. Stopped at ip=%d." % (opcode, ip), file=sys.stderr)
            sys.exit(1)

        # Keep the last few opcodes in memory
        previous_opcodes.pop()
        previous_opcodes.insert(0, opcode)

    return string_stack, int_stack, float_stack
