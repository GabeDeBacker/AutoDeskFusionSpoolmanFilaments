"""Fusion 360 application and user interface helpers."""

import adsk.core
APPLICATION = None
USER_INTERFACE = None
DESIGN = None

def get_design():
    """Return the current Fusion design instance."""
    global DESIGN
    if DESIGN is None:
        DESIGN = adsk.fusion.Design.cast(get_application().activeProduct)
    return DESIGN

def get_application():
    """Return the current Fusion application instance."""
    global APPLICATION
    if APPLICATION is None:
        APPLICATION = adsk.core.Application.get()
    return APPLICATION

def get_user_interface():
    """Return the current Fusion user interface instance."""
    global USER_INTERFACE
    if USER_INTERFACE is None:
        USER_INTERFACE = get_application().userInterface
    return USER_INTERFACE
