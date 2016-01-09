# TorqueVM Opcodes:
OPCODES = {
    0:      "OP_FUNC_DECL",
    1:      "OP_CREATE_OBJECT",
    2:      "OP_ADD_OBJECT",
    3:      "OP_END_OBJECT",
    4:      "OP_JMPIFFNOT",
    5:      "OP_JMPIFNOT",
    6:      "OP_JMPIFF",
    7:      "OP_JMPIF",
    8:      "OP_JMPIFNOT_NP",
    9:      "OP_JMPIF_NP",
    10:     "OP_JMP",
    11:     "OP_RETURN",
    12:     "OP_CMPEQ",
    13:     "OP_CMPGR",
    14:     "OP_CMPGE",
    15:     "OP_CMPLT",
    16:     "OP_CMPLE",
    17:     "OP_CMPNE",
    18:     "OP_XOR",
    19:     "OP_MOD",
    20:     "OP_BITAND",
    21:     "OP_BITOR",
    22:     "OP_NOT",
    23:     "OP_NOTF",
    24:     "OP_ONESCOMPLEMENT",
    25:     "OP_SHR",
    26:     "OP_SHL",
    27:     "OP_AND",
    28:     "OP_OR",
    29:     "OP_ADD",
    30:     "OP_SUB",
    31:     "OP_MUL",
    32:     "OP_DIV",
    33:     "OP_NEG",
    34:     "OP_SETCURVAR",
    35:     "OP_SETCURVAR_CREATE",
    36:     "OP_SETCURVAR_ARRAY",
    37:     "OP_SETCURVAR_ARRAY_CREATE",
    38:     "OP_LOADVAR_UINT",
    39:     "OP_LOADVAR_FLT",
    40:     "OP_LOADVAR_STR",
    41:     "OP_SAVEVAR_UINT",
    42:     "OP_SAVEVAR_FLT",
    43:     "OP_SAVEVAR_STR",
    44:     "OP_SETCUROBJECT",
    45:     "OP_SETCUROBJECT_NEW",
    47:     "OP_SETCURFIELD",
    48:     "OP_SETCURFIELD_ARRAY",
    49:     "OP_LOADFIELD_UINT",
    50:     "OP_LOADFIELD_FLT",
    51:     "OP_LOADFIELD_STR",
    52:     "OP_SAVEFIELD_UINT",
    53:     "OP_SAVEFIELD_FLT",
    54:     "OP_SAVEFIELD_STR",
    55:     "OP_STR_TO_UINT",
    56:     "OP_STR_TO_FLT",
    57:     "OP_STR_TO_NONE",
    58:     "OP_FLT_TO_UINT",
    59:     "OP_FLT_TO_STR",
    60:     "OP_FLT_TO_NONE",
    61:     "OP_UINT_TO_FLT",
    62:     "OP_UINT_TO_STR",
    63:     "OP_UINT_TO_NONE",
    64:     "OP_LOADIMMED_UINT",
    65:     "OP_LOADIMMED_FLT",
    66:     "OP_TAG_TO_STR",
    67:     "OP_LOADIMMED_STR",
    68:     "OP_DOCBLOCK_STR",
    69:     "OP_LOADIMMED_IDENT",
    70:     "OP_CALLFUNC_RESOLVE",
    71:     "OP_CALLFUNC",
    72:     "OP_ADVANCE_STR",
    73:     "OP_ADVANCE_STR_APPENDCHAR",
    74:     "OP_ADVANCE_STR_COMMA",
    75:     "OP_ADVANCE_STR_NUL",
    76:     "OP_REWIND_STR",
    77:     "OP_TERMINATE_REWIND_STR",
    78:     "OP_COMPARE_STR",
    79:     "OP_PUSH",
    80:     "OP_PUSH_FRAME",
    81:     "OP_BREAK",
    82:     "OP_INVALID",

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
    if version <= 36:
        if opcode >= 0x1000:  # Don't muddle my opcodes
            return opcode
        elif opcode >= 67:
            return opcode + 2
        elif opcode >= 46:
            return opcode + 1
    return opcode


def get_opcode(version, value):
    # Fix the opcode for scripts compiled with an old version.
    if version < 44:
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