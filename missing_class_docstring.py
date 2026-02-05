"""Sample module for testing PEP 257 compliance."""


class MyClassWithoutDocstring:
    def __init__(self):
        """Initialize the class."""
        self.value = 0
    
    def calculate(self):
        """Calculate something."""
        return self.value * 2


class AnotherClass:
    """This class has a proper docstring."""
    
    def method(self):
        """Method with docstring."""
        pass