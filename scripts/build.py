import os
import sys
import yaml

# TODO: check prefix, needs to be in installation dir

if 'ALL_CHANGED_FILES' in os.environ:
	desc_files = os.environ['ALL_CHANGED_FILES'].split(' ')
else:
	desc_files = []

print(f"Files changed: {desc_files}")

# Optional overrides, set from the workflow inputs (all may be empty)
extension_repository = os.environ.get('EXTENSION_REPOSITORY', '').strip()
extension_version = os.environ.get('EXTENSION_VERSION', '').strip()
platform = os.environ.get('PLATFORM', '').strip()

# Platforms known to extension-ci-tools (duckdb-ci matrix/extensions.json). Used to translate a single
# requested platform into the exclude/opt-in lists understood by extension-ci-tools build.yml
KNOWN_PLATFORMS = [
	'linux_amd64',
	'linux_amd64_musl',
	'linux_arm64',
	'linux_arm64_musl',
	'osx_amd64',
	'osx_arm64',
	'wasm_eh',
	'wasm_mvp',
	'wasm_threads',
	'windows_amd64',
	'windows_amd64_mingw',
	'windows_arm64',
]

if len(desc_files) > 1:
	raise ValueError('cannot have multiple descriptors changed or packages with spaces in their names')

deploy = True

if len(desc_files) == 0 or len(desc_files[0]) == 0:
	print("No changed files, only excel will be built as a test")
	desc_files = ['extensions/excel/description.yml']
	deploy = False

desc_file = desc_files[0]

with open(desc_file, 'r') as stream:
	desc = yaml.safe_load(stream)

print(desc)

# todo check other stuff like build system etc.

def split_list(value):
	return [item for item in (value or '').split(';') if item]

with open('env.sh', 'w+') as hdl:
	extension_github = extension_repository or desc['repo']['github']
	hdl.write(f"COMMUNITY_EXTENSION_GITHUB={extension_github}\n")
	extension_ref = desc['repo']['ref']
	if  os.environ['DUCKDB_VERSION'] != os.environ['DUCKDB_LATEST_STABLE']:
		if 'ref_next' in desc['repo']:
			extension_ref = desc['repo']['ref_next']
	if extension_version:
		extension_ref = extension_version
	hdl.write(f"COMMUNITY_EXTENSION_REF={extension_ref}\n")
	hdl.write(f"COMMUNITY_EXTENSION_NAME={desc['extension']['name']}\n")
	excluded_platforms = split_list(desc['extension'].get('excluded_platforms'))
	requires_toolchains = split_list(desc['extension'].get('requires_toolchains'))
	custom_toolchain_script = desc['extension'].get('custom_toolchain_script')
	vcpkg_url = desc['extension'].get('vcpkg_url')
	vcpkg_commit = desc['extension'].get('vcpkg_commit')
	opt_in_platforms = []
	if platform:
		if platform not in KNOWN_PLATFORMS:
			raise ValueError(f"unknown platform '{platform}', expected one of: {';'.join(KNOWN_PLATFORMS)}")
		if platform in excluded_platforms:
			raise ValueError(f"platform '{platform}' is listed in excluded_platforms of {desc_file}")
		# Build only the requested platform: exclude every other known platform and opt into this one
		# (opt-in makes sure reduced CI mode does not skip it)
		excluded_platforms = [p for p in KNOWN_PLATFORMS if p != platform]
		opt_in_platforms = [platform]
	hdl.write(f"COMMUNITY_EXTENSION_EXCLUDE_PLATFORMS={';'.join(excluded_platforms)}\n")
	hdl.write(f"COMMUNITY_EXTENSION_OPT_IN_PLATFORMS={';'.join(opt_in_platforms)}\n")
	# Build groups for extension-ci-tools build.yml: 'rust' is a toolchain of its own, everything else is an extra toolchain
	toolchain = 'rust' if 'rust' in requires_toolchains else 'main'
	extra_toolchains = [t for t in requires_toolchains if t != 'rust']
	hdl.write("COMMUNITY_EXTENSION_GROUPS<<EOF\n")
	hdl.write("main:\n")
	hdl.write("  config: extension_config.cmake\n")
	hdl.write(f"  toolchain: {toolchain}\n")
	if extra_toolchains:
		hdl.write(f"  extra_toolchains: {';'.join(extra_toolchains)}\n")
	hdl.write("EOF\n")
	if vcpkg_url:
		hdl.write(f"COMMUNITY_EXTENSION_VCPKG_URL={vcpkg_url}\n")
	if vcpkg_commit:
		hdl.write(f"COMMUNITY_EXTENSION_VCPKG_COMMIT={vcpkg_commit}\n")
	if deploy:
		hdl.write(f"COMMUNITY_EXTENSION_DEPLOY=1\n")
