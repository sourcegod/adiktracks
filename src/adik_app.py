#!/usr/bin/env python3
"""
    File: adik_app.py
    Bridge Interface between AdikPlayer class and the User Interface class
    Date: Sat, 16/08/2025
    Author: Coolbrother
"""
import os, sys
from adik_player import AdikPlayer

class AdikApp(object):
    """ Application manager for AdikPlayer """
    def __init__(self, ui_app=None):
        self._ui_app = ui_app  if ui_app is not None else None
        self.player = None
        self.mixer = None


    #----------------------------------------
    
    def display_message(msg, on_status_bar=False):
        """ Pass message to the User Interface, or display it """
        if self._ui_app is not None:
            self._ui_app.display_message(msg, on_status_bar)
        else:
            print(msg)
    
    #----------------------------------------

    def init_app(self, sample_rate=44100, block_size=256, num_output_channels=2, num_input_channels=1):
        self.player = AdikPlayer(sample_rate, block_size, num_output_channels, num_input_channels)
        self.mixer = self.player.mixer


    #----------------------------------------


#========================================

if __name__ == "__main__":
    # For testing
    app = AdikApp()
    app.init_app()
    input("It's OK...")
