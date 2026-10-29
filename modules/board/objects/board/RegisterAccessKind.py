"""
@module board.objects.board.RegisterAccessKind

RegisterAccessKind — one class per file (design §7). rm-2a (REGISTER_MAPPING_PLAN.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RegisterAccessKind(treeObject):
    """What it is: ONE WORD of the register-field access vocabulary - `rw`, `r`, `w1c`, `w0c`, `w-strobe`, `rw-toggle` - with what a READ of such a field
    does, what a WRITE does, the names the same behaviour has in the two register standards (IEEE 1800.2 UVM access policies, CMSIS-SVD access +
    modifiedWriteValues; "no exact" where neither has it), an example field from the cited ATmega328P table and the mistake it guards against (a
    read-modify-write that clears every pending flag). Every RegisterField's `access` is one of these rows' `name`.
    Code-owned: board.custom.register_access.ACCESS_KINDS (seeded, converged).
    Related concepts: `RegisterField.access`, `Register`.
    """

    plain_words = ('How a group of bits in a chip register behaves when the program reads it or writes it: some keep what you write, some only report, '
                   'some are cleared by writing a one or a zero, some act once when written. Each word has its own row saying exactly what it means.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', read_effect: str = '', write_effect: str = '', uvm_policy: str = '', svd_access: str = '',
                 example: str = '', caution: str = '', basis: str = '', manager=None):
        self.name = name                    # rw | r | w1c | w0c | w-strobe | rw-toggle (RegisterField.access)
        self.title = title                  # 'write one to clear'
        self.read_effect = read_effect      # what a read returns
        self.write_effect = write_effect    # what a write of 1 / 0 does
        self.uvm_policy = uvm_policy        # IEEE 1800.2 name (W1C ...) or '(no exact ...)'
        self.svd_access = svd_access        # CMSIS-SVD access + modifiedWriteValues
        self.example = example              # a field of the cited table that has it
        self.caution = caution              # the mistake it guards against
        self.basis = basis
