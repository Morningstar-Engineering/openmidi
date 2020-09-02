# openmidi
OpenMIDI is a community driven effort to document MIDI implementations of various MIDI devices. This information is made available at www.openmidi.com for public use.

# How to contribute
1. Fork the repository
2. Add your changes
   - Create a new yaml file
   - Update `mapping.json` file
   
3. Commit your changes
4. Create a pull request

# Instructions
The MIDI data for each device is saved in [yaml](https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html) files. 

The yaml files are organized in folders `data > brands`

Each yaml file follows a template (see template below)

After a new yaml file is created, the `mapping.json` file needs to be updated to map the brand and product name to the new file.

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


