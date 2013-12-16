verbosity=True

def verbose(text):
    if verbosity:
        print(text)

def setVerbose(v):
    global verbosity
    verbosity=v