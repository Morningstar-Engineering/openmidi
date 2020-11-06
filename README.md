# openmidi
OpenMIDI is a community driven effort to document MIDI implementations of various MIDI devices. This information is made available at www.openmidi.com for public use.

If you are new to Github, we have some basic instructions on setting up your account and doing your first Pull Request [here](https://morningstarengineering.atlassian.net/wiki/spaces/MMS/pages/219906049/Contributing+to+the+MIDI+Dictionary).

# Contributors
- [Huevos-y-Bacon](https://github.com/Huevos-y-Bacon)
- [Raphael Hüni](https://github.com/rafhun)
- [Daniel Gensberger](https://github.com/danielgensberger)
- [applekor](https://github.com/applekor)
- [Joel Lang](https://github.com/joellang)

# How to contribute
1. Fork the repository
2. Add your changes
   - Create a new yaml file
     - Check that your YAML file is valid: http://www.yamllint.com/
   - Update `mapping.json` file
     - Check that your JSON updates are valid: https://jsonlint.com/
   
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

    midi_channel: 
      instructions: |+
        [Description on how to set up the MIDI channel for the device]

    pc: 
      description: |+
        [Description on how PC messages work on the device]
    cc: 
      - name: [CC Function Name]
        value: [CC Number 0 - 127]
        description: [Description of function]
        type: [Parameter | System]
        min: [Minimum CC Value]
        max: [ Maximum CC Value]


