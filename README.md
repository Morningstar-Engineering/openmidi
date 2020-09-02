# openmidi
OpenMIDI is a community driven effort to document MIDI implementations of various MIDI devices. These information are then available at www.openmidi.com for public use.

# yaml Template
    midi_in: [TRS | Tip Active | Ring Active | DIN5 | USB]
    midi_thru: [Yes | No]
    phantom_power: [Yes | No]
    midi_clock: [Yes | No]

    midi_channel
      instructions: |+
        [Description on how to set up the MIDI channel for the device]

    pc
      description: |+
        [Description on how PC messages work on the device]
    cc
      - name: [CC Function Name]
        value: [CC Number 0 - 127]
        description: [Description of function]
        type: [Parameter | System]
        min: [Minimum CC Value]
        max: [ Maximum CC Value]

# How to contribute

If you are familiar with Github:
1. Clone the repository
2. Create a branch
3. Add your changes
4. Commit
5. Create a pull requests back to the Master branch
