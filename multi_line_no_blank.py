"""Module with multi-line docstring issues."""


def process_data(data):
    """Process the input data.
    This is a multi-line docstring that doesn't have
    a blank line after the summary line.
    Args:
        data: Input data
    Returns:
        Processed result
    """
    return data * 2


def proper_function():
    """Process data correctly.
    
    This has a proper blank line after the summary.
    
    Returns:
        Processed data
    """
    return True