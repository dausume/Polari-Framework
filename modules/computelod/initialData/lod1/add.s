	.file	"add.c"
	.option nopic
	.attribute arch, "rv32i2p1"
	.attribute unaligned_access, 0
	.attribute stack_align, 16
	.text
	.align	2
	.globl	add
	.type	add, @function
add:
	add	a0,a0,a1
	ret
	.size	add, .-add
	.ident	"GCC: (13.2.0-11ubuntu1+12) 13.2.0"
