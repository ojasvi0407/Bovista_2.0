def escape_configparser_value(value: str) -> str:
    """Escape interpolation markers before storing a value in ConfigParser."""
    return value.replace("%", "%%")
