from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().splitlines()

setup(
	name="kya_hr",
	version="0.0.1",
	description="Personnalisations RH et traductions pour KYA-Energy Group",
	author="KYA-Energy Group",
	author_email="info@kya-energy.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
