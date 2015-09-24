from hqcodedeployer.worker.processors.mkdir import MkDirWorker
from hqcodedeployer.worker.processors.tar import TarWorker, UnTarWorker
from hqcodedeployer.worker.processors.copy import CopyWorker
from hqcodedeployer.worker.processors.move import MoveWorker
from hqcodedeployer.worker.processors.git import Clone
from hqcodedeployer.worker.processors.bundle import Install as BundleInstall
from hqcodedeployer.worker.processors.symlink import Symlink
from hqcodedeployer.worker.processors.venv import Venv
from hqcodedeployer.worker.processors.file import Touch, Write, Download
from hqcodedeployer.worker.processors.rake import RakeWorker
from hqcodedeployer.worker.processors.bluepill import Bluepill
from hqcodedeployer.worker.processors.gem import Copy as GemCopy
from hqcodedeployer.worker.processors.pip import Install as PipInstall, Wheel as PipWheel
from hqcodedeployer.worker.processors.puppet import PuppetWorker
from hqcodedeployer.worker.processors.source import SourceWorker
from hqcodedeployer.worker.processors.chown import ChownWorker
from hqcodedeployer.worker.processors.chmod import ChmodWorker

processors = {
    'mkdir': MkDirWorker,
    'tar': TarWorker,
    'untar': UnTarWorker,
    'copy': CopyWorker,
    'move': MoveWorker,
    'git:clone': Clone,
    'bundle:install': BundleInstall,
    "symlink": Symlink,
    "venv": Venv,
    "file:touch": Touch,
    "file:write": Write,
    "file:download": Download,
    "rake": RakeWorker,
    "bluepill": Bluepill,
    "gem:copy": GemCopy,
    "pip:install": PipInstall,
    "pip:wheel": PipWheel,
    "puppet": PuppetWorker,
    "source": SourceWorker,
    "chown": ChownWorker,
    "chmod": ChmodWorker,
}
