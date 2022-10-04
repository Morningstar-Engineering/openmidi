# openmidi
OpenMIDI is a community driven effort to document the MIDI implementations of various MIDI devices for the benefit of all musicians. It aims to be the source of truth and reference via community feedback and contribution. 

This information is made available at www.openmidi.com or in this repository for public use. 

OpenMIDI is hosted free of charge by [Morningstar Engineering](https://www.morningstar.io)

If you are new to Github, we have some basic instructions on setting up your account and doing your first Pull Request [here](https://morningstarengineering.atlassian.net/wiki/spaces/MMS/pages/219906049/Contributing+to+the+MIDI+Dictionary).

# Contributors
Special thanks to all who have contributed! 
- [Huevos-y-Bacon](https://github.com/Huevos-y-Bacon)
- [Raphael Hüni](https://github.com/rafhun)
- [Daniel Gensberger](https://github.com/danielgensberger)
- [applekor](https://github.com/applekor)
- [Joel Lang](https://github.com/joellang)
- [andloubry](https://github.com/andloubry)
- [bzhgeek](https://github.com/bzhgeek)
- [fuzzy-phil](https://github.com/fuzzy-phil)
- [Harris Novick](https://github.com/lightyrs)

List is not updated.

# How to contribute
## If you are inclined to contribute via GitHub
1. Fork the repository
2. Add your changes
   - Create a new yaml file
     - Check that your YAML file is valid: http://www.yamllint.com/ (or https://codebeautify.org/yaml-validator)
   - Update `mapping.json` file
     - Check that your JSON updates are valid: https://jsonlint.com/
   
3. Commit your changes
4. Create a pull request

## If you want to use Microsoft Excel
We have created a template in Excel if you want to populate. In the repository, you will see a file called `openmidi_template.xlsx`. 
1. Download the Excel template
2. Populate the Excel file
3. Email it to help@morningstarfx.com with the subject `OpenMIDI - <Brand Name> - <Model Name>`
4. Our team will review the data, covert it to the required format and push it to the repository.

## Using the Webform
We have added a web-based form on OpenMIDI. Submissions will go into a queue which will be reviewed and added.
<img width="1170" alt="image" src="https://user-images.githubusercontent.com/6988852/193741306-50339e8d-39af-47a4-a33b-5d83af011c30.png">


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
        type: [Parameter | System] # Note: Parameter is a value to change (e.g., volume). System is a command to the device.
        min: [Minimum CC Value]
        max: [ Maximum CC Value]


