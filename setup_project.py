#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Creates or updates an mbed vscode project

Usage: setup_project.py [-t TOOLCHAIN] [-m TARGET] [-i IDE] [-o OPENOCD_ARGS] <mbed_project_dir>
   Defaults:
       TOOLCHAIN:    GCC_ARM
       TARGET:       NUCLEO_F429ZI
       IDE:          vscode_gcc_arm
       OPENOCD_ARGS: -f /usr/share/openocd/scripts/board/st_nucleo_f4.cfg -c "init" -c "reset init"
 E.g.
    cd ~/mbed
    vscode/setup_project.py blinky

 1) Creates new mbed project if <mbed_project_dir> does not exist. I.e. Runs "mbed new <mbed_project_dir>" etc
 2) Copies vscode tasks.json, launch.json from templates. Will overwrite if they exist.
 3) Copies main.cpp (blinky) from template. Only if it doesn't already exist.
 4) Copies keybindings.json to ~/.config/Code/User from template. Will overwrite if it exists.
 5) Copies .gitignore from templates to <mbed_project_dir>. Will overwrite if it exists.

"""
__author__  = "Lincoln Gill"
__version__ = "0.1.0"
__license__ = "GPLv3"

from jinja2 import Environment, FileSystemLoader
import os
import argparse

def get_args():
    """Parse the command line arguments
    Returns:
        parsed argument dictionary
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("mbed_project_dir", 
        help="mbed project directory. Creates a new project if directory does not exist")
    parser.add_argument("-t", "--toolchain", 
        help="Compile toolchain. E.g. GCC_ARM", 
        default="GCC_ARM")
    parser.add_argument("-m", "--target", 
        help="Compile target MCU. E.g. NUCLEO_F429ZI", 
        default="NUCLEO_F429ZI")
    parser.add_argument("-i", "--ide", 
        help="IDE to create project files for. E.g. vscode_gcc_arm", 
        default="vscode_gcc_arm")
    parser.add_argument("-o", "--openocd_args", 
        help="Command arguments for openocd command", 
        default="-f /usr/share/openocd/scripts/board/st_nucleo_f4.cfg -c \\\"init\\\" -c \\\"reset init\\\"")
    return parser.parse_args()

class TemplateFile:
    """Holds the Jinja2 template source and destination filenames and renders the output file

    Attributes:
        j2_filename (str):  Jinja2 template source filename
        out_filename (str): Full path to destination output file
        override (boolean): Overwrite the output file if it exists
        j2_env (:jinja2.Environment:, class_attr): Template loader object
    """

    __this_dir = os.path.dirname(os.path.abspath(__file__))
    __template_dir = os.path.join(__this_dir,"templates")
    j2_env = Environment(loader=FileSystemLoader(__template_dir),trim_blocks=True)

    def __init__(self, destdir, filename, override=True):
        """TemplateFile(args.mbed_project_dir, "main.cpp", override=False)
        Args:
            destdir (str): Directory path to destination output file
            filename (str): Basename of destination output file. Used to derive the source template filename
            override (boolean): Overwrite the output file during rendering, if it exists
        """
        self.j2_filename = filename+".j2"
        if filename[0] == '.': # Template filename will be missing leading "."
            self.j2_filename = filename[1:]+".j2"
        self.out_filename = os.path.join(destdir, filename)
        self.override = override

    def render(self, **kwargs):
        """Render template and write destination output file
        Only overwrites destination file if self.override is True
        Args:
            **kwargs: jinja2.Template.render() arguments. E.g. (template_var=replacement_value, ...)
        """
        if self.override or (not os.path.exists(self.out_filename)):
            print "Writing: "+self.out_filename
            out_file = open(self.out_filename,"w")
            out_file.write(TemplateFile.j2_env.get_template(self.j2_filename).render(kwargs))
            out_file.close()

class Project:
    """Represent the mbed project
    Attributes:
        projectdir (str):    Absolute path to the mbed project base directory
        vscodedir (str):     Absolute path to the <projectdir>/.vscode directory
        userconfigdir (str): Expanded value of ~/.config/Code/User/ Location of vscode keybindings config file.
        toolchain (str):     mbed toolchain value
        target (str):        mbed target value
        ide (str):           mbed export IDE value
        openocd_args (str):  Command arguments for launching openocd. Includes board/module config filenames
    """

    @classmethod
    def os_cmd(cls, cmd):
        """Print out and Execute an OS command
        Args:
            cmd (str): OS command to execute
        """
        print "%s..." % cmd
        os.system(cmd)

    def create_project(self):
        """Create a new mbed project in the project directory. Do nothing if the project directory already exists."""
        if not os.path.exists(self.projectdir):
            Project.os_cmd("mbed new %s" % self.projectdir)
            old_dir = os.getcwd()
            os.chdir(self.projectdir)
            Project.os_cmd("mbed update")
            Project.os_cmd("mbed toolchain %s" % self.toolchain)
            Project.os_cmd("mbed target %s" % self.target)
            Project.os_cmd("mbed config --list")
            Project.os_cmd("mbed export -m %s -i %s" % (self.target, self.ide))
            if os.path.exists("Makefile"):
                print "Renaming Makefile to Makefile.dontuse"
                os.rename("Makefile", "Makefile.dontuse")
            os.chdir(old_dir)

    def __init__(self, args):
        """Project(args)
        Creates a new mbed project directory, exported to use with vscode
        Args:
            args (list): parsed args from argparse.ArgumentParser(). Requires:
                args.mbed_project_dir (str): Base directory of the mbed project
                args.toolchain (str):        mbed toolchain (-t)
                args.target (str):           mbed target (-m)
                args.ide (str):              ide string for mbed export -i
                args.openocd_args (str):     String of openocd args to go into the vscode launch.json file
        """
        self.projectdir = os.path.abspath(args.mbed_project_dir)
        self.vscodedir = os.path.join(self.projectdir, ".vscode")
        self.userconfigdir = os.path.join(os.path.expanduser("~"),".config","Code","User")
        self.toolchain = args.toolchain
        self.target = args.target
        self.ide = args.ide
        self.openocd_args = args.openocd_args
        self.create_project()

    def render_templates(self):
        """Render templates and write output files to correct locations

        Takes the created mbed project and customises it to use mbed commands for build, debug and serial terminal
        """
        for filename in ["tasks.json", "launch.json"]:
            TemplateFile(self.vscodedir, filename, override=True).render(
                toolchain=self.toolchain,
                target=self.target,
                openocd_args=self.openocd_args
            )
        TemplateFile(self.projectdir,    "main.cpp",         override=False).render()
        TemplateFile(self.projectdir,    ".gitignore",       override=True).render()
        TemplateFile(self.userconfigdir, "keybindings.json", override=True).render()

if __name__ == '__main__':
    Project(get_args()).render_templates()