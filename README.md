# Setup: 
You need python3 with hid module. Install python, install pip and run: `pip install hid `

# Using:
You can either run it from the CMD with CLI commands for both the pooling rate and the DPI `--250 --1600` or directly, in which case you can input the chosen values. Only a limited amount of DPIs and Pooling Rates are availible due to the firmware being very strict about which hex values are acceptable. CLI example through autohotkey: `Run, "path/to/python" "path/to/the/script" "--1000 --8000", , Hide`

# Contributing:
Just as any other USB hid device, USB sniffing was very effective for finding out how to communicate with the device. Wireshark + USBPcap did the job. If you want, change settings in the official XD7 driver and register the payload for different states.

# Acknowledgements:
Thanks to [LowByteProductions](http://https://www.youtube.com/@LowByteProductions "LowByteProductions") for the quality content, it was very helpful.
