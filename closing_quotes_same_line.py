"""Module with closing quotes issue."""


def bad_multi_line():
    """Multi-line docstring with closing quotes issue.
    
    This is a longer description that explains more details.
    However, the closing quotes are on the same line. 
    """
    return True


def good_multi_line():
    """Multi-line docstring with proper closing quotes.
    
    This has closing quotes on their own line.   """
    return False


class BadClass:
    """Class with bad closing quotes.
    
    Description here.    """
    
    def bad_method(self):
        """Method with bad quotes.
        
        Some text. """
        pass