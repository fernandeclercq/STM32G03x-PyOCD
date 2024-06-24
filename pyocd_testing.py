
from pyocd.core.soc_target import SoCTarget
from pyocd.probe.debug_probe import DebugProbe
from pyocd.probe.stlink_probe import StlinkProbe
from pyocd.core.target import Target
from pyocd.core.session import Session


from pyocd.core.helpers import ConnectHelper
from pyocd.flash.file_programmer import FileProgrammer
import time
import os

import enum

import logging
logger = logging.getLogger("pogoProgrammer")


class STM32G030SWDInterface:
    """ STM32G030 SWD Interface """
    
    class ReadProtection(enum.Enum):
        PROTECTION_DISABLED = 0xAA
        PROTECTION_ENABLED = 0xBB
    
    # 0x1FFF7590 UUID Address (3 byte long)
    
    class FlashPeripheral:
        """ Flash Peripheral Definitions """
        BASE_ADDR                 = 0x40022000                        # Flash Base Address
        KEY_REGISTER              = BASE_ADDR + 0x008           # Flash Key Register Address
        KEY_1                     = 0x45670123                        # Flash Key 1 for Flash unlock sequence
        KEY_2                     = 0xCDEF89AB                        # Flash Key 2 for Flash unlock sequence
        
        OPTION_KEY_REGISTER       = BASE_ADDR + 0x00C           # Flash Option Key register Address
        OPTION_KEY_1              = 0x08192A3B                        # Flash Option Key 1 for Option unlock sequence
        OPTION_KEY_2              = 0x4C5D6E7F                        # Flash Option Key 2 for Option unlock sequence
    
        
        STATUS_REGISTER           = BASE_ADDR + 0x010           # Flash Status Register Address
        SR_CFGBSY_MASK            = 0x40000                           # Flash SR - Programming or Erase configuration busy flag
        SR_BSY1_MASK              = 0x10000                           # Flash SR - Bank 1 busy flag
        SR_PGSERR_MASK            = 0x80                              # Flash SR - Programming Sequence Error Flag (PROGERR,SIZERR, PGAERR, WRPERR, MISSERR or FASTERR)
        
        CONTROL_REGISTER          = BASE_ADDR + 0x014           # Flash Control Register Address
        CR_OPTLOCK_MASK           = 0x40000000                        # Flash CR - Flash Lock Flag (bit 31)
        CR_FLASH_LOCK_MASK        = 0x80000000                        # Flash CR - Flash Options Lock Flag (bit 30)
        CR_OBL_LAUNCH_MASK        = 0x8000000                         # Flash CR - Option byte load launch (bit 27)
        CR_OPTSTRT_MASK           = 0x20000                           # Flash CR - Start of modification of option bytes (bit 17)
        CR_STRT_MASK              = 0x10000                           # Flash CR - Start Erase Operation (bit 16)
        CR_MER1_MASK              = 0x4                               # Flash CR - Mass Erase Request (bit 2)
        
        OPTION_REGISTER           = BASE_ADDR + 0x020           # Flash Option Register Address
        OPTR_RDP_MASK             = 0xFF                              # Flash OR - Read Protection Level (bit 7:0) [ Level 0 = 0xAA; Level 1 = BB; Level 2 = CC]
        OPTR_WITHOUT_RDP_MASK     = 0xFFFFFF00                        # Flash OR - Option Register without RDP
        
        
        
    def __init__(self, probe : DebugProbe | StlinkProbe, bin_file_path : str, frequency : int   = 24000000, target : str = "stm32g030f6px", delay : float = 0.5) -> None:
        self._pyocdOptions : dict[str, any] = {
            "target_override": target,
            "connect_mode" : 'under-reset',
            "reset_type": "hw",
            #"logging":"pyocd.yaml",
            "frequency": frequency,
        }
        self._probe : DebugProbe | StlinkProbe = probe 
        self._bin_file_path : str = bin_file_path
        self._uuid : list[int] = []
        self._delay : float = delay
        
    @property
    def uuid(self) -> list[int]:
        return self._uuid
        
    def __waitBusyBank1(self, target : SoCTarget):
        bank1_busy = 1
        while bank1_busy != 0:
            bank1_busy = target.read32(self.FlashPeripheral.STATUS_REGISTER) & self.FlashPeripheral.SR_BSY1_MASK
            logger.debug("Waiting for bank1 to become available for write/read")
            
    def __waitBusyProgrammingErasing(self, target : SoCTarget):
        is_busy = 1
        while is_busy != 0:
            is_busy = target.read32(self.FlashPeripheral.STATUS_REGISTER) & self.FlashPeripheral.SR_CFGBSY_MASK
            logger.debug("Waiting for Programming/Erase operations to be finished")
        
    def __unlockFlash(self, target : SoCTarget):
        """ Performs unlock Flash is the FLASH_LOCK flag is set. """
        is_flash_locked = target.read32(self.FlashPeripheral.CONTROL_REGISTER) & self.FlashPeripheral.CR_FLASH_LOCK_MASK
        
        self.__waitBusyBank1(target)
        self.__waitBusyProgrammingErasing(target)
        
        if is_flash_locked != 0: # Flash Lock Flag is still set
            logger.info("Unlocking Flash...")
            
            # Write Key1 and Key2 to Key Register(Flash Peripheral) to unlock the Flash
            target.write32(self.FlashPeripheral.KEY_REGISTER, self.FlashPeripheral.KEY_1)
            target.write32(self.FlashPeripheral.KEY_REGISTER, self.FlashPeripheral.KEY_2)
            
            # Wait until the Busy flag for bank1 is reset
            self.__waitBusyBank1(target=target)
            
            # Wait until programming/erasing flag is reset
            self.__waitBusyProgrammingErasing(target=target)
            
            #TODO Check if flash lock flag is 0 now
        else:
            logger.info("Flash already unlocked! Skipping unlocking...")
        
    
    def __unlockOptions(self, target : SoCTarget):
        is_options_lock = target.read32(self.FlashPeripheral.CONTROL_REGISTER) & self.FlashPeripheral.CR_OPTLOCK_MASK
        
        if is_options_lock != 0:
            logger.info("Unlocking Options...")
            
            # Write Option Key 1 and Option Key 2 to Option Key Register to unlock the Options
            target.write32(self.FlashPeripheral.OPTION_KEY_REGISTER, self.FlashPeripheral.OPTION_KEY_1)
            target.write32(self.FlashPeripheral.OPTION_KEY_REGISTER, self.FlashPeripheral.OPTION_KEY_2)
            
            # Wait for operations to finished
            self.__waitBusyBank1(target=target)
            self.__waitBusyProgrammingErasing(target=target)
            
            #TODO Check if the options lock flag is 0 now
            
        else:
            logger.info("Options already unlocked! Skipping unlocking...")
            
    def __getOptionRegister(self, target : SoCTarget) -> int:
        result = target.read32(self.FlashPeripheral.OPTION_REGISTER)
        logger.debug("Option Register: {}".format(result.to_bytes(4, byteorder='big')))
        return result
    
    def __getRDPByte(self, target : SoCTarget) -> int:
        result = self.__getOptionRegister(target) & self.FlashPeripheral.OPTR_RDP_MASK
        logger.debug("Option byte: {}".format(result.to_bytes(1, byteorder='big')))
        return result
    
    def __getControlRegister(self, target : SoCTarget) -> int:
        result = target.read32(self.FlashPeripheral.CONTROL_REGISTER)
        logger.debug("Control Register: {}".format(result.to_bytes(4, byteorder='big')))
        return result
    
    
    def __setOptionLevel(self, target : SoCTarget, rdp_level : ReadProtection):
        option_register = self.__getOptionRegister(target) & self.FlashPeripheral.OPTR_WITHOUT_RDP_MASK
        
        new_options = option_register | rdp_level.value
        
        target.write32(self.FlashPeripheral.OPTION_REGISTER, new_options)
        logger.info("Setting RDP level to: {}".format(rdp_level.value.to_bytes(1, byteorder='big')))
        
        self.__waitBusyBank1(target)
        self.__waitBusyProgrammingErasing(target)
        
    
    def __commitOptionsModificationChange(self, target : SoCTarget):
        control_reg = self.__getControlRegister(target)
        
        logger.info("Committing RDP level changes....")
        # Set Option Start Bit
        target.write32(self.FlashPeripheral.CONTROL_REGISTER, (control_reg | self.FlashPeripheral.CR_OPTSTRT_MASK))
        
        self.__waitBusyBank1(target)
        self.__waitBusyProgrammingErasing(target)
    
    def __launchLoadOptionsOperation(self, target : SoCTarget):
        control_reg = self.__getControlRegister(target)
        
        # Make sure that any other operation (Programming/Erasing) is finished
        self.__waitBusyBank1(target)
        self.__waitBusyProgrammingErasing(target)
        
        logger.info("Loading New RDP Level into Flash...")
        # Set OBL Bit
        target.write32(self.FlashPeripheral.CONTROL_REGISTER, (control_reg | self.FlashPeripheral.CR_OBL_LAUNCH_MASK))
    
    
    def disableRDP(self):
        """ Disables Read Data Protection(RDP) if Level 1 is active on the device """
        logger.info("Performing Disable Read Data Protection!")
        with ConnectHelper.session_with_chosen_probe(unique_id=self._probe.unique_id, options = self._pyocdOptions) as session:
            _board  = session.board
            _target : SoCTarget = _board.target
            
            _target.reset_and_halt()
            
            while not _target.is_halted():
                logger.debug("waiting for target to halt")

            rdp_level = self.__getRDPByte(target=_target)
            logger.info("Current RDP Level: {}".format(rdp_level.to_bytes(1, byteorder='big')))
            
            if rdp_level == 0xCC:
                logger.error("Device is Locked with LEVEL 2! Device is Bricked!")
                raise Exception("Impossible to remove RDP level 2!")
            else:
                if rdp_level == self.ReadProtection.PROTECTION_DISABLED.value:
                    logger.info("RDP is not enabled!, skipping operation...")
                    return
                elif rdp_level == self.ReadProtection.PROTECTION_ENABLED.value:
                    logger.info("RDP is Enabled!")
                    
                    self.__unlockFlash(target=_target)
            
                    self.__unlockOptions(target=_target)
                    
                    self.__setOptionLevel(target=_target, rdp_level=self.ReadProtection.PROTECTION_DISABLED)
                    
                    self.__commitOptionsModificationChange(target=_target)
                    
                    # Force Load Options (This will trigger a MCU Reset)
                    self.__launchLoadOptionsOperation(target=_target)
                    
                    
                else:
                    logger.error(f"Unknown RDP level: {rdp_level}")
                    raise Exception("Unknown RDP level!")
                
            session.close()
        time.sleep(self._delay)
            
    
    def saveDeviceUUID(self):
        """ Logs the Device UUID to the console """
        logger.info("Reading UUID from device...")
        with ConnectHelper.session_with_chosen_probe(unique_id=self._probe.unique_id, options = self._pyocdOptions) as session:
            _board  = session.board
            _target : SoCTarget = _board.target
            
            _target.reset_and_halt()
            
            while not _target.is_halted():
                logger.debug("waiting for target to halt")
                
            uuid_bytes = _target.read_memory_block32(0x1FFF7590, 3)
            for idx, uuid_byte in enumerate(uuid_bytes, start=0):
                logger.info("UUID Byte [{}] : {}".format(
                    idx,
                    ' '.join(f'0x{b:02x} ' for b in uuid_byte.to_bytes(4, byteorder='big'))
                ))
                logger.debug("UUID Byte [{}] : {}".format(idx, uuid_byte.to_bytes(4, byteorder='big')))
                self._uuid.append(uuid_byte)
        
        
            session.close()
        time.sleep(self._delay)
    
    def __programmerCallback(self, progress : float):
        logger.info("Programming progress: {}%".format(round((progress * 100), 2)))
    
    
    def programDevice(self):
        """ Programs the Device with the configured bin-file """
        logger.info("Performing Programming Device with file: {}!".format(self._bin_file_path))
        
        if not os.path.exists(self._bin_file_path):
            logger.error(f"The file path: {self._bin_file_path} was not found!")
            raise Exception(f"The file path: {self._bin_file_path} was not found!")
        
        with ConnectHelper.session_with_chosen_probe(unique_id=self._probe.unique_id, options = self._pyocdOptions) as session:
            _board  = session.board
            _target : SoCTarget = _board.target
            
            
            _target.reset_and_halt()
            while not _target.is_halted():
                logger.debug("waiting for target to halt")
            
            logger.info("Target reset and halted!")
            
            self.__waitBusyBank1(_target)
            self.__waitBusyProgrammingErasing(_target)
            
            programmer = FileProgrammer(
                session,
                self.__programmerCallback
            )
            programmer.program(self._bin_file_path)
            logger.info("Device programmed successfully!")
            
            session.close()
        time.sleep(self._delay)
    
    
    def enableRDP(self):
        """ Enables Read Data Protection(RDP) if Level 1 on the device """
        logger.info("Performing Enabling Read Data Protection!")
        with ConnectHelper.session_with_chosen_probe(unique_id=self._probe.unique_id, options = self._pyocdOptions) as session:
            _board  = session.board
            _target : SoCTarget = _board.target
            
            _target.reset_and_halt()
            
            while not _target.is_halted():
                logger.debug("waiting for target to halt")

            rdp_level = self.__getRDPByte(target=_target)
            logger.info("Current RDP Level: {}".format(rdp_level.to_bytes(1, byteorder='big')))
            
            if rdp_level == 0xCC:
                logger.error("Device is Locked with LEVEL 2! Device is Bricked!")
                raise Exception("Impossible to remove RDP level 2!")
            else:
                if rdp_level == self.ReadProtection.PROTECTION_DISABLED.value:
                    logger.info("RDP is not enabled!, Enabling RDP....")
                    self.__unlockFlash(target=_target)
            
                    self.__unlockOptions(target=_target)
                    
                    self.__setOptionLevel(target=_target, rdp_level=self.ReadProtection.PROTECTION_ENABLED)
                    
                    self.__commitOptionsModificationChange(target=_target)
                    
                    # Force Load Options (This will trigger a MCU Reset)
                    self.__launchLoadOptionsOperation(target=_target)
                    
                    return
                elif rdp_level == self.ReadProtection.PROTECTION_ENABLED.value:
                    logger.info("RDP is Enabled!, skipping operation...")

                else:
                    logger.error(f"Unknown RDP level: {rdp_level}")
                    raise Exception("Unknown RDP level!")
                
            session.close()
        time.sleep(self._delay)
    
    
    def checkRDP(self, rdp_level_check : ReadProtection):
        """ Check if the RDP is Enabled """
        logger.info("Checking the RDP Level after locking device with level 1 Protection!")
        with ConnectHelper.session_with_chosen_probe(unique_id=self._probe.unique_id, options = self._pyocdOptions) as session:
            _board  = session.board
            _target : SoCTarget = _board.target
            
            _target.reset_and_halt()
            
            while not _target.is_halted():
                logger.debug("waiting for target to halt")
                
            rdp_level = self.__getRDPByte(target=_target)
            logger.info("Current RDP Level: {}".format(rdp_level.to_bytes(1, byteorder='big')))
            
            if rdp_level == rdp_level_check.value:
                logger.info("RDP Level Matches the Check! - RDP Level : {}".format(rdp_level.to_bytes(1, byteorder='big')))
                
            else:
                logger.error("RDP Level does not match the requested level. Failed")
                raise Exception("RDP Level does not match the requested level. Failed")
        
        
            session.close()
        time.sleep(self._delay)        
                
        
