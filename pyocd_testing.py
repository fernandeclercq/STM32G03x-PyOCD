from pyocd.core.soc_target import SoCTarget
from pyocd.probe.debug_probe import DebugProbe
from pyocd.probe.stlink_probe import StlinkProbe
from pyocd.core.target import Target
from pyocd.core.session import Session


from pyocd.core.helpers import ConnectHelper
from pyocd.flash.file_programmer import FileProgrammer, ProgressCallback
import time


import logging
# logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("pogoProgrammer")


probes : list[DebugProbe | StlinkProbe] = ConnectHelper.get_all_connected_probes()

def test_pro_call(progress : float):
    logger.info(f"progress {progress}%")


def perform_some_operation(probe : DebugProbe | StlinkProbe):
    with ConnectHelper.session_with_chosen_probe(
            unique_id=probe.unique_id, 
            options = {
                "target_override": "stm32g030f6px",
                "connect_mode" : 'under-reset',
                "reset_type": "hw",
                "logging":"pyocd.yaml",
                "frequency": 4000000,
            }) as session:
        board  = session.board
        target : SoCTarget = board.target
    
        
        # Load firmware into device.
        file_programmer = FileProgrammer(
            session,
            test_pro_call,
            )
        
        
        
        class STM32G030SWDInterface:

            class FlashPeripheral:
                FLASH_BASE_ADDR                 = 0x40022000                        # Flash Base Address
                FLASH_KEY_REGISTER              = FLASH_BASE_ADDR + 0x008           # Flash Key Register Address
                FLASH_KEY_1                     = 0x45670123                        # Flash Key 1 for Flash unlock sequence
                FLASH_KEY_2                     = 0xCDEF89AB                        # Flash Key 2 for Flash unlock sequence
                
                FLASH_OPTION_KEY_REGISTER       = FLASH_BASE_ADDR + 0x00C           # Flash Option Key register Address
                FLASH_OPTION_KEY_1              = 0x08192A3B                        # Flash Option Key 1 for Option unlock sequence
                FLASH_OPTION_KEY_2              = 0x4C5D6E7F                        # Flash Option Key 2 for Option unlock sequence
            
                
                FLASH_STATUS_REGISTER           = FLASH_BASE_ADDR + 0x010           # Flash Status Register Address
                FLASH_SR_CFGBSY_MASK            = 0x40000                           # Flash SR - Programming or Erase configuration busy flag
                FLASH_SR_BSY1_MASK              = 0x10000                           # Flash SR - Bank 1 busy flag
                FLASH_SR_PGSERR_MASK            = 0x80                              # Flash SR - Programming Sequence Error Flag (PROGERR,SIZERR, PGAERR, WRPERR, MISSERR or FASTERR)
                
                FLASH_CONTROL_REGISTER          = FLASH_BASE_ADDR + 0x014           # Flash Control Register Address
                FLASH_CR_OPTLOCK_MASK           = 0x80000000                        # Flash CR - Flash Lock Flag (bit 31)
                FLASH_CR_FLASH_LOCK_MASK        = 0x40000000                        # Flash CR - Flash Options Lock Flag (bit 30)
                FLASH_CR_OBL_LAUNCH_MASK        = 0x8000000                         # Flash CR - Option byte load launch (bit 27)
                FLASH_CR_OPTSTRT_MASK           = 0x20000                           # Flash CR - Start of modification of option bytes (bit 17)
                FLASH_CR_STRT_MASK              = 0x10000                           # Flash CR - Start Erase Operation (bit 16)
                FLASH_CR_MER1_MASK              = 0x4                               # Flash CR - Mass Erase Request (bit 2)
                
                FLASH_OPTION_REGISTER           = FLASH_BASE_ADDR + 0x020           # Flash Option Register Address
                FLASH_OPTR_RDP_MASK             = 0xFF                              # Flash OR - Read Protection Level (bit 7:0) [ Level 0 = 0xAA; Level 1 = BB; Level 2 = CC]
                FLASH_OPTR_WITHOUT_RDP_MASK     = 0xFFFFFF00                        # Flash OR - Option Register without RDP
                
                
                
            def __init__(self, probe : DebugProbe | StlinkProbe, bin_file_path : str, frequency : int   = 4000000, target : str = "stm32g030f6px") -> None:
                self._options : dict[str, any] = {
                    "target_override": target,
                    "connect_mode" : 'under-reset',
                    "reset_type": "hw",
                    "logging":"pyocd.yaml",
                    "frequency": frequency,
                }
                self._serial_number : str = probe.unique_id
                self._bin_file_path : bin_file_path
                
                
                
            
            def disableRDP(self):
                
                pass
            
            def saveDeviceUUID(self):
                pass
            
            def programDevice(self):
                pass
            
            def enableRDP(self):
                pass
            
            def checkRDP(self):
                pass
                
        
        FLASH_BASE_ADDR = 0x40022000 
        
        FLASH_KEY_REGISTER = FLASH_BASE_ADDR + 0x008
        
        FLASH_KEY_1 = 0x45670123
        FLASH_KEY_2 = 0xCDEF89AB
        
        FLASH_OPTION_KEY_REGISTER = FLASH_BASE_ADDR + 0x00C
        
        FLASH_OPTION_KEY_1 = 0x08192A3B
        FLASH_OPTION_KEY_2 = 0x4C5D6E7F
    
        
        FLASH_STATUS_REGISTER = FLASH_BASE_ADDR + 0x010
        
        FLASH_OPTION_REGISTER = FLASH_BASE_ADDR + 0x020
        
        FLASH_CONTROL_REGISTER = FLASH_BASE_ADDR + 0x014
        
        
        FLASH_SR_CFGBSY_MASK = 0x40000 # Programming or Erase configuration busy
        FLASH_SR_BSY1_MASK = 0x10000 # Busy Bank 1
        FLASH_SR_PGSERR_MASK = 0x80 # Program or Erase Error Mask
        FLASH_SR_OPTLOCK_MASK = 0x40000000
        FLASH_SR_FLASH_LOCK_MASK = 0x80000000
        
        FLASH_CR_MER1 = 0x4 # Mask Mass Erase Request
        FLASH_CR_STRT = 0x10000 # Mask Start Erase Operation
        
        FLASH_OPTR_RDP_MASK = 0xFF
        FLASH_OPTR_WITHOUT_RDP_MASK = 0xFFFFFF00
        FLASH_CR_OPTSTRT_MASK = 0x20000 # Start of modification of option bytes
        FLASH_CR_OBL_LAUNCH_MASK = 0x8000000 # Option byte load launch
        
        def wait_for_busy_bank1():
            result = 1
            while result !=0:
                result = target.read32(FLASH_STATUS_REGISTER) & FLASH_SR_BSY1_MASK
                print("waiting for Bank 1 Busy Flag")
                
        def check_programming_sequence_error():
            res = target.read32(FLASH_STATUS_REGISTER) & FLASH_SR_PGSERR_MASK
            print(res.to_bytes(4, byteorder='big'))
            if res == 1:
                print("Programming Sequence Error!")
                print("Clearing Program Sequence Error Flags")
                #write 1 to PGSERR Bit
                new = res | FLASH_SR_PGSERR_MASK
                target.write32(FLASH_STATUS_REGISTER, new)
        
        def wait_for_busy_programming_erasing():
            result = 1
            while result !=0:
                result = target.read32(FLASH_STATUS_REGISTER) & FLASH_SR_CFGBSY_MASK
                print("waiting for Programming or Erase Busy Flag")
                
        def set_mass_erase_request_bank1():
            flash_control_register = target.read32(FLASH_CONTROL_REGISTER)
            print(flash_control_register)
            print(flash_control_register.to_bytes(4, byteorder='big'))
            new = flash_control_register | FLASH_CR_MER1
            print(new)
            print(new.to_bytes(4, byteorder='big'))
            target.write32(FLASH_CONTROL_REGISTER, new)
            
            
        def set_start_erase_operation():
            flash_control_register = target.read32(FLASH_CONTROL_REGISTER)
            print(flash_control_register)
            print(flash_control_register.to_bytes(4, byteorder='big'))
            new = flash_control_register | FLASH_CR_STRT
            print(new)
            print(new.to_bytes(4, byteorder='big'))
            target.write32(FLASH_CONTROL_REGISTER, new)
            
        def start_option_mod_operation():
            control_reg = get_flash_control_register()
            
            wait_for_busy_bank1()
            wait_for_busy_programming_erasing()
            
            target.write32(FLASH_CONTROL_REGISTER, (control_reg | FLASH_CR_OPTSTRT_MASK))
            
            wait_for_busy_bank1()
            wait_for_busy_programming_erasing()
            
        def start_option_load_operation():
            control_reg = get_flash_control_register()
            wait_for_busy_bank1()
            wait_for_busy_programming_erasing()
            target.write32(FLASH_CONTROL_REGISTER, (control_reg | FLASH_CR_OBL_LAUNCH_MASK))
            
        def unlock_flash():
            # Check if the FLASH_LOCK is already off
            
            flash_lock = target.read32(FLASH_CONTROL_REGISTER)
            flash_lock_val = flash_lock & FLASH_SR_FLASH_LOCK_MASK
            
            if flash_lock_val != 0:
                print("unlocking flash...")
            
                target.write32(FLASH_KEY_REGISTER, FLASH_KEY_1)
                target.write32(FLASH_KEY_REGISTER, FLASH_KEY_2)
                
                wait_for_busy_bank1()
                wait_for_busy_programming_erasing()
                
            else:
                print("Flash already unlocked!")
            
        def unlock_option():
            # Check if the OPTION_LOCK is already off
            option_lock = target.read32(FLASH_CONTROL_REGISTER) 
            option_lock_val = option_lock & FLASH_SR_OPTLOCK_MASK

            if option_lock_val != 0:
                print("unlocking option")
                
                # Write opt keys consecutively to unlock Flash CR register(erase / programming operations)
                target.write32(FLASH_OPTION_KEY_REGISTER, FLASH_OPTION_KEY_1)
                target.write32(FLASH_OPTION_KEY_REGISTER, FLASH_OPTION_KEY_2)
                
                wait_for_busy_bank1()
                wait_for_busy_programming_erasing()
            else:
                print("Option already unlocked!")
                
        def get_flash_option_register() -> int:
            wait_for_busy_bank1()
            wait_for_busy_programming_erasing()
            return target.read32(FLASH_OPTION_REGISTER)
        
        def get_flash_control_register() -> int:
            wait_for_busy_bank1()
            wait_for_busy_programming_erasing()
            return target.read32(FLASH_CONTROL_REGISTER)
        
        def set_option_level_1():
            option_register = get_flash_option_register() & FLASH_OPTR_WITHOUT_RDP_MASK
            print(option_register.to_bytes(4, byteorder='big'))
            new_val = option_register | 0xBB
            print("Writing BB to option register")
            
            target.write32(FLASH_OPTION_REGISTER, new_val)
            
        
        def set_option_level_0():
            option_register = get_flash_option_register() & FLASH_OPTR_WITHOUT_RDP_MASK
            print(option_register.to_bytes(4, byteorder='big'))
            new_val = option_register | 0xAA
            print("Writing BB to option register")
            
            target.write32(FLASH_OPTION_REGISTER, new_val)
            

            
        def get_read_protection_byte():
            result : int = 0
            
            result = get_flash_option_register() & FLASH_OPTR_RDP_MASK
            
            return result
            
            
        def perform_mass_erase():
            
            target.reset_and_halt()
            
            unlock_flash()
                       
            check_programming_sequence_error()
            
            set_mass_erase_request_bank1()
            
            set_start_erase_operation()
            
            wait_for_busy_bank1()
            wait_for_busy_programming_erasing()
            
        
        def enable_read_protection():
            
            target.reset_and_halt()
            
            unlock_flash()

            unlock_option()
            
            opt_byte = get_read_protection_byte()
            
            print(opt_byte.to_bytes(1, byteorder='big'))
            
            if opt_byte == 0xCC:
                raise Exception("Euh... do you got a new stm32g030?")

            else:
                if opt_byte == 0xAA:
                    print("Lock Level 0")
                    
                    # Set Lock Level BB (Level 1)
                    set_option_level_1()
                    
                    start_option_mod_operation()
                    
                    # wait for Bank 1 to become free
                    wait_for_busy_bank1()
                    wait_for_busy_programming_erasing()
                    
                    # This operation loads the changed value of the RDP(Read Data Protection) and performs a hard reset on the MCU
                    start_option_load_operation()
                    
                elif opt_byte == 0xBB:
                    print("Lock Level 1")
                    
                    proc = get_read_protection_byte()
                    print(proc.to_bytes(1, byteorder='big'))
            
        def disable_read_protection():
            target.reset_and_halt()
            
            unlock_flash()
            
            unlock_option()
            
            opt_byte = get_read_protection_byte()
            
            print(opt_byte.to_bytes(1, byteorder='big'))
            
            if opt_byte == 0xCC:
                raise Exception("Euh... do you got a new stm32g030?")

            else:
                if opt_byte == 0xAA:
                    print("Lock Level 0")
                    
                    # Set Lock Level BB (Level 1)
                    # set_option_level_1()
                    
                    # start_option_mod_operation()
                    
                    # # wait for Bank 1 to become free
                    # wait_for_busy_bank1()
                    # wait_for_busy_programming_erasing()
                    
                    # # This operation loads the changed value of the RDP(Read Data Protection) and performs a hard reset on the MCU
                    # start_option_load_operation()
                    
                elif opt_byte == 0xBB:
                    print("Lock Level 1")
                    
                    # Set Lock Level AA (Level 0)
                    set_option_level_0()
                    
                    start_option_mod_operation()
                    
                    
                    start_option_load_operation()
                    
                    
                    
            
            
            pass
        
        #perform_mass_erase()
        #disable_read_protection()
        
        
        
        #perform_mass_erase()
        
        target.reset_and_halt()
        
        #file_programmer.program("./LibraryDevelopment.bin")
        
        target.reset(Target.ResetType.HW)
        
        # Disconnect from the Target
        session.close()
        
        # wait some time
        time.sleep(1)
        





for probe in probes:
    perform_some_operation(probe)
    
    


