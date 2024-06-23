# STM32G03x-PyOCD
Simple script to perform Programming/Erasing actions with STLink via pyocd module.

In the "pyocd_testing.py" you will find basic SWD operations:
- Mass Erasing the Flash Memory
- Setting Level 1 Read Protection to the Flash (RDP Level 1)
  - Enabling Read protection
- Setting Level 0 Read Protection to the Flash (RDP Level 0)
  - Disabling Read Protection
 
All of these procedures are described in the Reference Manual for the STM32G030F6Px:
- https://www.st.com/resource/en/reference_manual/rm0454-stm32g0x0-advanced-armbased-32bit-mcus-stmicroelectronics.pdf&ved=2ahUKEwjo0qez6fGGAxWX3AIHHV7KDv8QFnoECBYQAQ&usg=AOvVaw3lSwbTb5IyN9LnayPYfHpf

Under the third section "3. Embedded Flash memory (FLASH)"

Feel free to fork or correct some of the procedures! Enjoy!
