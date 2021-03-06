#!/usr/bin/env python3

import os
import sys
import argparse

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)


class MPRISPlayer:
    """Represents an MPRIS-compatible player."""

    def __init__(self, bus_name, session_bus, format_string):
        # User-provided fields
        self.session_bus = session_bus
        self.bus_name = bus_name
        self.format_string = format_string

        # D-Bus related fields
        self.proxy_object = self.session_bus.get_object(
            bus_name,
            '/org/mpris/MediaPlayer2'
        )
        self.properties_interface = dbus.Interface(
            self.proxy_object,
            'org.freedesktop.DBus.Properties'
        )
        self.player_interface = dbus.Interface(
            self.proxy_object,
            'org.mpris.MediaPlayer2.Player'
        )

        # Connection to signal
        self.connection = None

        # Player metadata
        self.is_playing = None
        self.metadata = {
            'title': "",
            'artist': [],
            'album': ""
        }

        # D-Bus seems to send multiple signals when properties are changed,
        # so let's fix that
        self.prev_content = None

        # Initialize metadata
        self.update_status()

    # D-Bus method wrappers

    def play(self):
        (self.player_interface.get_dbus_method("Play"))()

    def pause(self):
        (self.player_interface.get_dbus_method("Pause"))()

    def playpause(self):
        (self.player_interface.get_dbus_method("PlayPause"))()

    def stop(self):
        (self.player_interface.get_dbus_method("Stop"))()

    def previous(self):
        (self.player_interface.get_dbus_method("Previous"))()

    def next(self):
        (self.player_interface.get_dbus_method("Next"))()

    def get(self, interface, target):
        return (self.properties_interface.get_dbus_method("Get"))(interface, target)

    # D-Bus signal handler

    def on_PropertiesChanged(self, interface, changed_props, invalid_props):
        if interface == self.player_interface.dbus_interface:

            updated = self.update_status(changed_props)

            if updated:
                self.print_status()

    # Helper function

    def connect(self):
        self.connection = self.proxy_object.connect_to_signal(
            'PropertiesChanged',
            self.on_PropertiesChanged
        )

    def disconnect(self):
        self.connection.remove()

    def update_status(self, changed_props=None):
        if changed_props:

            # If position is changed
            if 'Position' in changed_props:
                return False

            # If metadata is changed
            if 'Metadata' in changed_props:
                for key in changed_props['Metadata'].keys():
                    normal_key = key[6:]
                    if normal_key in self.metadata.keys() \
                       and self.metadata[normal_key] != changed_props['Metadata'][key]:
                        self.metadata[normal_key] = changed_props['Metadata'][key]

                        return True

            # If playback status is changed
            if 'PlaybackStatus' in changed_props:
                if changed_props['PlaybackStatus'] == 'Playing':
                    self.is_playing = True
                elif changed_props['PlaybackStatus'] == 'Paused':
                    self.is_playing = False
                else:
                    self.is_playing = None

                return True

            return False

        else:
            try:
                raw_metadata = self.get(
                    'org.mpris.MediaPlayer2.Player',
                    'Metadata'
                )
                for key in self.metadata.keys():
                    if 'xesam:' + key in raw_metadata:
                        self.metadata[key] = raw_metadata['xesam:' + key]
                    else:
                        self.metadata[key] = ''

                playback = self.get(
                    'org.mpris.MediaPlayer2.Player',
                    'PlaybackStatus'
                )
                if playback == 'Playing':
                    self.is_playing = True
                elif playback == 'Paused':
                    self.is_playing = False
                else:
                    self.is_playing = None

                return True

            except dbus.DBusException:
                print("METADATA UNAVAILABLE")
                return False

    def print_status(self):

        result = replace_tag(self.format_string, self.metadata)

        if self.is_playing:
            result = replace_block(result, 'playing')
            result = replace_block(result, 'paused', '')
        else:
            result = replace_block(result, 'playing', '')
            result = replace_block(result, 'paused')

        if result != self.prev_content:
            print_always(result)
            self.prev_content = result


class NonePlayer(MPRISPlayer):

    def __init__(self):
        pass

    # D-Bus method wrappers

    def play(self):
        pass

    def pause(self):
        pass

    def playpause(self):
        pass

    def stop(self):
        pass

    def previous(self):
        pass

    def next(self):
        pass

    def get(self, interface, target):
        pass

    # Helper function

    def connect(self):
        pass

    def disconnect(self):
        pass

    def print_status(self):
        pass


class MPRISManager:
    """Manages multiple MPRIS players."""

    def __init__(self, format_string):
        self.format_string = format_string

        self.session_bus = dbus.SessionBus()

        self.players = {}
        self.primary_player = NonePlayer()
        self.populate_players()
        self.update_players()

        self.session_bus.add_signal_receiver(
            self.on_NameOwnerChanged,
            'NameOwnerChanged'
        )

    def populate_players(self):
        for name in self.session_bus.list_names():
            if MPRISManager.is_player_bus(name):
                owner = self.session_bus.get_name_owner(name)
                self.add_player(name, owner)

    def add_player(self, bus_name, owner):
        self.players[owner] = MPRISPlayer(
            bus_name,
            self.session_bus,
            self.format_string
        )

    def del_player(self, owner):
        del self.players[owner]

    def change_owner(self, old_owner, new_owner):
        temp = self.players[old_owner]
        del self.players[old_owner]
        self.players[new_owner] = temp

    def update_players(self):
        for _, player in self.players.items():
            if isinstance(player.is_playing, bool):
                if self.primary_player is player:
                    return
                else:
                    self.primary_player.disconnect()
                    self.primary_player = player
                    self.primary_player.connect()
                    return
            else:
                continue

        print("NO ACTIVE PLAYERS")

    # D-Bus signal handler

    def on_NameOwnerChanged(self, name, old_owner, new_owner):
        if MPRISManager.is_player_bus(name):
            if not old_owner and new_owner:
                self.add_player(name, old_owner)
            elif not new_owner and old_owner:
                self.del_player(old_owner)
            else:
                self.change_owner(old_owner, new_owner)
            self.update_players()

    # Helper function

    @staticmethod
    def is_player_bus(bus_name):
        return bus_name.startswith('org.mpris.MediaPlayer2')


# Functions that don't belong anywhere


def print_always(content: str):
    print(content)
    sys.stdout.flush()


def replace_tag(original: str, value_dict: dict):
    result = original
    for tag_name in value_dict.keys():
        value = None
        if isinstance(value_dict[tag_name], list):
            value = value_dict[tag_name][0]
        else:
            value = value_dict[tag_name]

        result = result.replace('{{' + tag_name + '}}', value)

    return result


def replace_block(original: str, block_name: str, replace_str: str = None):
    result = None

    block_begin = '{{' + block_name + '}}'
    block_end = '{{/' + block_name + '}}'

    start_pos = original.find(block_begin)
    end_pos = original.find(block_end)

    if isinstance(replace_str, str):
        result = \
            original[:start_pos] \
            + replace_str \
            + original[end_pos + len(block_end):]
    else:
        result = original \
            .replace(block_begin, '') \
            .replace(block_end, '')

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Control MPRIS players from command line."
    )
    parser.add_argument(
        'command',
        nargs='?',
        choices=[
            'status',
            'tail',
            'scroll',
            'previous',
            'next',
            'play',
            'pause',
            'playpause',
            'stop',
            'help'
        ],
        default='status',
        help="Specify the action for manager to take."
    )
    parser.add_argument(
        '--format', '-f',
        nargs='?',
        default="{{playing}}Playing: {{/playing}}{{paused}}Paused: {{/paused}}{{artist}} - {{title}}",
        help="Change the default status format."
    )
    parser.add_argument(
        '--limit', '-l',
        nargs='?',
        default=30,
        type=int,
        help="Number of characters to display when showing status."
    )
    parser.add_argument(
        '--exclude', '-e',
        action='append',
        type=str,
        help="Players to exclude from appearing."
    )
    args = parser.parse_args()

    manager = MPRISManager(args.format)

    if args.command == 'status':
        manager.primary_player.print_status()

    elif args.command == 'tail':
        manager.primary_player.print_status()

        loop = GLib.MainLoop()
        try:
            loop.run()
        finally:
            loop.quit()

    elif args.command == 'scroll':
        pass

    elif args.command == 'previous':
        manager.primary_player.previous()

    elif args.command == 'next':
        manager.primary_player.next()

    elif args.command == 'play':
        manager.primary_player.play()

    elif args.command == 'pause':
        manager.primary_player.pause()

    elif args.command == 'playpause':
        manager.primary_player.playpause()

    elif args.command == 'stop':
        manager.primary_player.stop()

    elif args.command == 'help':
        parser.print_help()

if __name__ == "__main__":
    main()
