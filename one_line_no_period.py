"""Module with docstring ending with period."""


def function_with_bad_docstring():
    """Calculate value without period"""
    return 42


def function_with_good_docstring():
    """Calculate value with proper period."""
    return 42


class TestClass:
    """Class docstring without period"""
    
    def method(self):
        """Method with no period"""
        pass