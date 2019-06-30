import warnings

def my_show_warnings(msg,*args,**kwargs):
    return "{}: {}\n".format(args[0].__name__,msg)

warnings.formatwarning = my_show_warnings

class FireflyError(Exception):
    pass

class FireflyWarning(Warning):
    pass

class FireflyMessage(Warning):
    pass
