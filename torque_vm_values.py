# TorqueVM Opcodes:
OPCODES = {
    0:      "OP_FUNC_DECL",
    1:      "OP_CREATE_OBJECT",
    2:      "OP_ADD_OBJECT",
    3:      "OP_END_OBJECT",
    4:      "OP_FINISH_OBJECT",
    5:      "OP_JMPIFFNOT",
    6:      "OP_JMPIFNOT",
    7:      "OP_JMPIFF",
    8:      "OP_JMPIF",
    9:      "OP_JMPIFNOT_NP",
    10:     "OP_JMPIF_NP",
    11:     "OP_JMP",
    12:     "OP_RETURN",
    13:     "OP_RETURN_VOID",
    14:     "OP_CMPEQ",
    15:     "OP_CMPGR",
    16:     "OP_CMPGE",
    17:     "OP_CMPLT",
    18:     "OP_CMPLE",
    19:     "OP_CMPNE",
    20:     "OP_XOR",
    21:     "OP_MOD",
    22:     "OP_BITAND",
    23:     "OP_BITOR",
    24:     "OP_NOT",
    25:     "OP_NOTF",
    26:     "OP_ONESCOMPLEMENT",
    27:     "OP_SHR",
    28:     "OP_SHL",
    29:     "OP_AND",
    30:     "OP_OR",
    31:     "OP_ADD",
    32:     "OP_SUB",
    33:     "OP_MUL",
    34:     "OP_DIV",
    35:     "OP_NEG",
    36:     "OP_SETCURVAR",
    37:     "OP_SETCURVAR_CREATE",
    38:     "OP_SETCURVAR_ARRAY",
    39:     "OP_SETCURVAR_ARRAY_CREATE",
    40:     "OP_LOADVAR_UINT",
    41:     "OP_LOADVAR_FLT",
    42:     "OP_LOADVAR_STR",
    43:     "OP_SAVEVAR_UINT",
    44:     "OP_SAVEVAR_FLT",
    45:     "OP_SAVEVAR_STR",
    46:     "OP_SETCUROBJECT",
    47:     "OP_SETCUROBJECT_NEW",
    48:     "OP_SETCUROBJECT_INTERNAL",
    49:     "OP_SETCURFIELD",
    50:     "OP_SETCURFIELD_ARRAY",
    51:     "OP_SETCURFIELD_TYPE",
    52:     "OP_LOADFIELD_UINT",
    53:     "OP_LOADFIELD_FLT",
    54:     "OP_LOADFIELD_STR",
    55:     "OP_SAVEFIELD_UINT",
    56:     "OP_SAVEFIELD_FLT",
    57:     "OP_SAVEFIELD_STR",
    58:     "OP_STR_TO_UINT",
    59:     "OP_STR_TO_FLT",
    60:     "OP_STR_TO_NONE",
    61:     "OP_FLT_TO_UINT",
    62:     "OP_FLT_TO_STR",
    63:     "OP_FLT_TO_NONE",
    64:     "OP_UINT_TO_FLT",
    65:     "OP_UINT_TO_STR",
    66:     "OP_UINT_TO_NONE",
    67:     "OP_LOADIMMED_UINT",
    68:     "OP_LOADIMMED_FLT",
    69:     "OP_TAG_TO_STR",
    70:     "OP_LOADIMMED_STR",
    71:     "OP_DOCBLOCK_STR",
    72:     "OP_LOADIMMED_IDENT",
    73:     "OP_CALLFUNC_RESOLVE",
    74:     "OP_CALLFUNC",
    75:     "OP_ADVANCE_STR",
    76:     "OP_ADVANCE_STR_APPENDCHAR",
    77:     "OP_ADVANCE_STR_COMMA",
    78:     "OP_ADVANCE_STR_NUL",
    79:     "OP_REWIND_STR",
    80:     "OP_TERMINATE_REWIND_STR",
    81:     "OP_COMPARE_STR",
    82:     "OP_PUSH",
    83:     "OP_PUSH_FRAME",
    84:     "OP_ASSERT",
    85:     "OP_BREAK",
    86:     "OP_ITER_BEGIN",
    87:     "OP_ITER_BEGIN_STR",
    88:     "OP_ITER",
    89:     "OP_ITER_END",
    90:     "OP_INVALID",

    # From here on, values added by me to help decompilation
    0x1000:     "META_ELSE",
    0x1001:     "META_ENDIF",
    0x1002:     "META_ENDWHILE_FLT",
    0x1003:     "META_ENDWHILE",
    0x1004:     "META_ENDFUNC",
    0x1005:     "META_END_BINARYOP",
}

METADATA = {
    "META_ELSE":            0x1000,
    "META_ENDIF":           0x1001,
    "META_ENDWHILE_FLT":    0x1002,
    "META_ENDWHILE":        0x1003,
    "META_ENDFUNC":         0x1004,
    "META_END_BINARYOP":    0x1005,
}

COMPARISON = {
    "OP_CMPEQ": "==",
    "OP_CMPLT": "<",
    "OP_CMPNE": "!=",
    "OP_CMPGR": ">",
    "OP_CMPGE": ">=",
    "OP_CMPLE": "<=",
}


# Fixes opcodes for legacy Torque versions.
def translate_opcode(version, opcode):
    if opcode >= 0x1000:  # Don't muddle my opcodes
        return opcode
    if version <= 36:
        if opcode >= 67:
            return opcode + 2
        elif opcode >= 46:
            return opcode + 1
    elif version <= 44:
        if opcode >= 82:
            return opcode + 4
        elif opcode >= 81:
            return opcode + 4
        elif opcode >= 49:
            return opcode + 3
        elif opcode >= 12:
            return opcode + 2
        elif opcode >= 4:
            return opcode + 1
    return opcode


def get_opcode(version, value):
    # Fix the opcode for scripts compiled with an old version.
    if version < 47:
        value = translate_opcode(version, value)
    if value in OPCODES:
        return OPCODES[value]
    else:
        return None


STRING_OPERATORS = {
    "\t":   "TAB",
    "\n":   "NL",
    " ":    "SPC"
}

CALL_TYPES = {
    0:  "FunctionCall",
    1:  "MethodCall",
    2:  "ParentCall"
}