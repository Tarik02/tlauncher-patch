#!/usr/bin/env python3

import re
import sys
import os
from pathlib import Path
from shutil import copyfile, copytree, rmtree


if len(sys.argv) != 3:
	print('Usage: python patch.py <input jar> <output jar>')
	exit(0)

ORIGINAL_JAR = Path(sys.argv[1]).resolve()
OUTPUT_JAR = Path(sys.argv[2]).resolve()
WORKDIR = Path.cwd()/'workdir'


def shellquote(s: str):
    return "'" + str(s).replace("'", "'\\''") + "'"


def clear_dir(path: Path):
	if path.exists():
		rmtree(path)
	path.mkdir()


def clone_krakatau():
	if (Path.cwd()/'Krakatau').exists():
		print('Krakatau is here.')
	else:
		print('Clonning Krakatau...')
		os.system('git clone https://github.com/Storyyeller/Krakatau.git')
		print('Krakatau was clonned.')


def cleanup():
	print('Cleaning up...')
	if WORKDIR.exists():
		rmtree(WORKDIR)
	print('Cleaning up successful.')
	WORKDIR.mkdir()


def extract():
	print('Extracting...')
	clear_dir(WORKDIR/'extracted')
	os.system(f"unzip {shellquote(ORIGINAL_JAR)} -d {shellquote(WORKDIR/'extracted')} > /dev/null")
	print('Extracting successful.')


def disassemble():
	print('Disassembling...')
	clear_dir(WORKDIR/'disassembled')
	os.system(f"python Krakatau/disassemble.py -roundtrip -out {shellquote(WORKDIR/'disassembled')} -path {shellquote(ORIGINAL_JAR)} org/tlauncher/tlauncher/minecraft/auth/Account.class > /dev/null")
	print('Disassembling successful.')


def patch():
	print('Patching...')
	successful = False
	with (WORKDIR/'disassembled'/'org'/'tlauncher'/'tlauncher'/'minecraft'/'auth'/'Account.j').open('r') as inf:
		method_index = None
		while True:
			line = inf.readline()
			if not line:
				break
			match = re.match(r'^\.const \[(\d+)\] = Utf8 isPremiumAccount \n$', line)
			if match is not None:
				method_index = match.group(1)
				break

	(WORKDIR/'patched'/'org'/'tlauncher'/'tlauncher'/'minecraft'/'auth').mkdir(parents=True, exist_ok=True)

	with \
		(WORKDIR/'disassembled'/'org'/'tlauncher'/'tlauncher'/'minecraft'/'auth'/'Account.j').open('r') as inf, \
		(WORKDIR/'patched'/'org'/'tlauncher'/'tlauncher'/'minecraft'/'auth'/'Account.j').open('w') as outf \
	:
		if method_index is not None:
			while True:
				line = inf.readline()
				if not line:
					break

				match = re.match(r'^\.method public \[(\d+)\] : \[(\d+)\] \n$', line)
				if match and match.group(1) == method_index:
					successful = True
					outf.write(line)
					outf.write(inf.readline())  #    .attribute [*] .code stack * locals *
					inf.readline()  # L0:     aload_0
					inf.readline()  # L1:     getfield [*]
					outf.write('L0:     iconst_1 \n')
					continue

				outf.write(line)

	if not successful:
		print('Patch failed :(')
	else:
		print('Patch successful :)')


def assemble():
	print('Assembling...')
	os.system(f"python Krakatau/assemble.py -out {shellquote(WORKDIR/'assembled')} {shellquote(WORKDIR/'patched'/'org'/'tlauncher'/'tlauncher'/'minecraft'/'auth'/'Account.j')}")
	print('Assembling successful.')


def patch_jar():
	print('Patching jar...')
	if (WORKDIR/'patched_jar').exists():
		rmtree(WORKDIR/'patched_jar')
	copytree(WORKDIR/'extracted', WORKDIR/'patched_jar')
	copyfile(
		WORKDIR/'assembled'/'org'/'tlauncher'/'tlauncher'/'minecraft'/'auth'/'Account.class',
		WORKDIR/'patched_jar'/'org'/'tlauncher'/'tlauncher'/'minecraft'/'auth'/'Account.class',
	)
	for fn in os.listdir(WORKDIR/'patched_jar'/'META-INF'):
		#if fn.endswith('.RSA') or fn.endswith('.SF') or fn.endswith('.MF'):
		if fn.endswith('.RSA') or fn.endswith('.SF'):
			(WORKDIR/'patched_jar'/'META-INF'/fn).unlink()
	print('Patching jar successful.')


def build_jar():
	print('Building jar...')
	os.system(f"cd {shellquote(WORKDIR/'patched_jar')} && zip -q -r {shellquote(WORKDIR/'patched.jar')} .")


def sign_jar():
	clear_dir(WORKDIR/'signing')
	os.system(' '.join([
		'cd', shellquote(WORKDIR/'signing'),
		'&&',
		'keytool',
		'-genkey',
		'-noprompt',
		'-alias', 'alias1',
		'-dname', '"CN=, OU=, O=, L=, S=, C="',
		'-keystore', 'keystore',
		'-storepass', 'password',
		'-keypass', 'password',
	]))
	copyfile(WORKDIR/'patched.jar', WORKDIR/'signed.jar')
	os.system(' '.join([
		'cd', shellquote(WORKDIR/'signing'),
		'&&',
		'jarsigner',
		shellquote(WORKDIR/'signed.jar'),
		'alias1',
		'-keystore', 'keystore',
		'-storepass', 'password',
		'-keypass', 'password',
	]))


clone_krakatau()
cleanup()
extract()
disassemble()
patch()
assemble()
patch_jar()
build_jar()
sign_jar()
copyfile(WORKDIR/'signed.jar', OUTPUT_JAR)
print('DONE!')
