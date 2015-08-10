from setuptools import setup, find_packages


installRequires = []
dependencyLinks = []

with open("requirements.txt", "r") as reqfile:
  for line in reqfile:
    line = line.strip()
    (link, _, package) = line.rpartition("#egg=")
    if link:
      # e.g., "-e https://YOMPhub.com/vitaly-krugl/haigha/tarball/master#egg=haigha-0.7.4rc100"
      if line.startswith("-e"):
        line = line[2:].strip()

      dependencyLinks.append(line)

      (packageName, _, packageVersion) = package.partition("-")

      package = packageName + "==" + packageVersion

    installRequires.append(package)



setup(
  name = "nta.utils",
  description = "Numenta common utilities",
  packages = find_packages(),
  include_package_data=True,
  install_requires = installRequires,
  dependency_links = dependencyLinks
)
