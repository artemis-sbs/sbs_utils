from enum import Enum
import re
import ast
import os
from pathlib import Path
from .. import fs
from zipfile import ZipFile

from ..agent import Agent
import logging
import random

import sys
from ..helpers import format_exception
import json
from .mast_globals import MastGlobals
from .mast_node import MastNode, Scope

class SourceMapData:
    def __init__(self, file_name, basedir):
        self.file_name = file_name
        self.basedir = basedir
        self.is_lib = False

    def __str__(self):
        return f"{self.file_name} ({self.basedir})"

debug_logger = None
def DEBUG(msg):
    global debug_logger
    if debug_logger is None:
        # create logger with 'spam_application'
        debug_logger = logging.getLogger('debug')
        debug_logger.setLevel(logging.DEBUG)
        # create file handler which logs even debug messages
        fh = logging.FileHandler('debug.log', mode='w')
        fh.setLevel(logging.DEBUG)
        debug_logger.addHandler(fh)
    debug_logger.debug(msg)



class Rule:
    def __init__(self, re, cls):
        self.re = re
        self.cls = cls



def first_non_space_index(s):
    for idx, c in enumerate(s):
        if not c.isspace():
            return idx
        if c == '\n':
            return idx
    return len(s)


def first_non_newline_index(s):
    for idx, c in enumerate(s):
        if c != '\n':
            return idx
    return len(s)

def first_non_whitespace_index(s):
    nl = 0
    nl_idx=0
    for idx, c in enumerate(s):
        if c != '\n' and c != '\t' and c != ' ':
            return (idx,nl, nl_idx)
        if c == '\n':
            nl+=1
            nl_idx = idx
    return (len(s), nl, nl_idx)

def first_newline_index(s):
    for idx, c in enumerate(s):
        if c == '\n':
            return idx
    return len(s)


class ExpParseData:
    def __init__(self):
        self.in_string = False
        self.paren = 0
        self.bracket = 0
        self.brace = 0
        self.is_assign = False
        self.is_block = False
        self.idx = -1
        self.double_assign = False

    @property
    def in_something(self):
        return self.in_string or (self.paren>0) or (self.bracket>0) or (self.brace>0)
    @property
    def is_valid(self):
        return not (self.in_something or self.double_assign)

def find_exp_end(s, expect_block):
    data = ExpParseData()

    for idx, c in enumerate(s):
        if c == '\n' and not data.in_something:
            data.idx = idx
            return data
        if c == '=' and not data.in_something and not data.is_assign:
            data.is_assign = True
            continue
        elif c == '=' and not data.in_something and data.is_assign:
            data.double_assign = True
            return data
        
        if c == ':' and not data.in_something and expect_block:
            data.is_block = True
            data.idx = idx
            return data
        
        if c == '(' and not data.in_string:
            data.paren+=1
            continue
        if c == ')' and not data.in_string:
            data.paren-=1
            continue
        if c == '[' and not data.in_string:
            data.bracket+=1
            continue
        if c == ']' and not data.in_string:
            data.bracket-=1
            continue
        if c == '{' and not data.in_string:
            data.brace+=1
            continue
        if c == '}' and not data.in_string:
            data.brace-=1
            continue
        if c == '"' and not data.in_string:
            data.in_string = True
            continue
        if c == '"' and data.in_string:
            data.in_string = False
            continue

    data.idx = len(s)
    return data

class InlineData:
    def __init__(self, start, end):
        self.start = start
        self.end = end


# IMPORTING other nodes should not happen here
# It can screw up the order
from .core_nodes.comment import Comment
#### This one really break stuff
#### from .core_nodes import Assign



class Mast():
    include_code = False

    
    inline_count = 0
    source_map_files = []
    imported = {}

    def __init__(self, cmds=None, is_import=False):
        super().__init__()

        self.lib_name = None
        self.is_import = is_import
        self.basedir = None
        self.parent_basedir = None
        self.compiler_errors = []
                

        if cmds is None:
            self.clear("no_mast_file", self)
            return
        if isinstance(cmds, str):
            cmds = self.compile(cmds, "<string>")
        # else:
        #     self.build(cmds)

        

    def make_global(func):
        add_to = MastGlobals.globals
        add_to[func.__name__] = func


    def make_global_var(name, value):
        MastGlobals.globals[name] = value
        
    

    def import_python_module_for_source(self, name, lib_name):
        import importlib, importlib.abc

        class StringLoader(importlib.abc.SourceLoader):
            def __init__(self, data):
                self.data = data

            def get_source(self, fullname):
                return self.data
            
            def get_data(self, path):
                return self.data.encode("utf-8")
            
            def get_filename(self, fullname):
                return "<not a real path>/" + fullname + ".py"

        module_name = name[:-3]
        if sys.modules.get(module_name) is None:
            spec = None
            if self.lib_name is not None:
                #module_parent = str(Path(self.lib_name).stem)
                #if self.basedir is not  None:
                #    module_name = str(Path().joinpath(module_parent, self.basedir, module_name).as_posix()).replace("/", ".")
                #elif self.parent_basedir is not None:
                #    module_name = str(Path().joinpath(module_parent, self.parent_basedir, module_name).as_posix()).replace("/", ".")

                #module_name = self.lib_name
                content, errors = self.content_from_lib_or_file(name)
                if content is None:
                    raise Exception(f"Failed to import python in mast library {name} {self.lib_name}")
                loader = StringLoader(content)
                spec = importlib.util.spec_from_loader(module_name, loader, origin="built-in")
            else:
                # if its not in this dir try the mission script dir
                if os.path.isfile(os.path.join(self.basedir, name)):
                    import_file_name = os.path.join(self.basedir, name)
                else:
                    import_file_name = os.path.join(fs.get_mission_dir(), name)
                spec = importlib.util.spec_from_file_location(module_name, import_file_name)
            
            if spec is not None:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                MastGlobals.import_python_module(module_name)
            else:
                lib_name = lib_name if self.lib_name is None else lib_name
                raise Exception(f"Failed to import python in mast library {name} {lib_name}")



    nodes = MastNode.nodes

    def get_source_file_name(file_num):
        if file_num is None:
            return "<string>"
        if file_num >= len(Mast.source_map_files):
            return "<unknown>"
        return str(Mast.source_map_files[file_num])

    def clear(self, file_name, root):
        from .core_nodes import Label

        self.inputs = {}
        if not self.is_import:
            #self.set_inventory_value("mast", self)
            Agent.SHARED.set_inventory_value("SHARED", Agent.SHARED.get_id())
            Mast.source_map_files = []
            

        # self.vars = {"mast": self}
        self.labels = {}
        self.inline_labels = {}
        main = Label("main")
        if root is not None:
            main = root.labels.get("main", main)
        self.labels["main"] = main
        self.labels["$NOOP$"] = Label("$NOOP$")
        self.cmd_stack = [main]
        self.indent_stack = [0]
        self.main_pruned = False
        #self.lib_name = None
        #### runtime
        self.schedulers = set()
        self.signal_observers = {}

        map_data = SourceMapData(file_name, self.basedir)
        if self.lib_name is not None:
            map_data.basedir = self.lib_name
            map_data.is_lib = True


        Mast.source_map_files.append(map_data)
        return len(Mast.source_map_files)-1
                
    
    def prune_main(self):
        from .core_nodes.assign import Assign

        if self.main_pruned:
            return
        main = self.labels.get("main")
        # Convert all the assigned from the main into comments
        # removing is bad it will affect if statements
        # If statements may run twice?
        #
        if main is not None:
            for i in range(len(main.cmds)):
                cmd = main.cmds[i]
                if cmd.__class__ == Assign and cmd.scope == Scope.SHARED:
                    main.cmds[i] = Comment()
            self.main_pruned = True

    def add_scheduler(self, scheduler):
        self.schedulers.add(scheduler)

    def refresh_schedulers(self, source, label):
        """TODO: Deprecate for signals?

        Args:
            source (_type_): _description_
            label (_type_): _description_
        """
        for scheduler in self.schedulers:
            if scheduler == source:
                continue
            scheduler.refresh(label)


    def signal_register(self, name, task, label_info):
        if label_info.server and not task.main.is_server():
            return

        task_map = self.signal_observers.get(name, {})
        info_list = task_map.get(task, [])
        info_list.append(label_info)
        task_map[task] = info_list
        self.signal_observers[name] = task_map

    def signal_unregister(self, name, task):
        #
        # note:
        #    Not sure this is written logically correct
        #
        info = self.signal_observers.get(name,None)
        if info is None:
            return
        if task in info:
            del info[task]
            self.signal_observers[name] = info

    def signal_unregister_all(self, task):
        #
        # note:
        #    Not sure this is written logically correct
        #
        for name in self.signal_observers:
            info = self.signal_observers[name]
            if info is None:
                return
            if task in info:
                del info[task]
                self.signal_observers[name] = info

    def signal_unregister_all_inline(self, task):
        # Look for any signal using the task
        for name in self.signal_observers:
            info = self.signal_observers[name]
            if info is None:
                return
            # If the loc is not 0 its inline and not jump
            if task in info:
                info_list = [i for i in info[task] if i.is_jump]
                if len(info_list)==0:
                    del info[task]
                elif len(info_list) != len(info[task]):
                    # print(f"Purged {name}")
                    info[task] = info_list
            self.signal_observers[name] = info

    def signal_emit(self, name, sender_task, data):
        # Copy so we can remove if needed
        tasks = self.signal_observers.get(name, {}).copy()
        #
        #TODO: This should remove finished tasks
        #
        for task in tasks:
            if task.done():
                self.signal_unregister(name, task)
                continue
            label_info_list = tasks[task]
            for label_info in label_info_list:
                if label_info.server and not task.main.is_server():
                    continue
                task.emit_signal(name, sender_task, label_info, data)

    def update_shared_props_by_tag(self, tag, props, test):
        for scheduler in self.schedulers:
            if scheduler.page is not None:
                scheduler.page.update_props_by_tag(tag, props, test)


    def remove_scheduler(self, scheduler):
        # End and remove all tasks
        for task in scheduler.tasks:
            task.end()
            scheduler.tasks.remove(task)
        self.schedulers.remove(scheduler)

    def find_imports(self, folder):
        import os
        imports = []
        for root, dirs, files in os.walk(os.path.join(self.basedir, folder)):
            # Avoids dev .git or .build, .add_ons etc.
            if os.path.basename(root).startswith("."):
                continue
            for name in files:
                if name.endswith("__init__.mast"):
                    p = os.path.join(root, name)
                    #DEBUG(p)
                    imports.append(p)
        return imports
    
    def find_add_ons(self, folder):
        import os
        addons = []
        for root, dirs, files in os.walk(os.path.join(self.basedir, folder)):
            # Avoids dev .git or .build, .add_ons etc.
            if os.path.basename(root).startswith("."):
                continue

            for name in files:
                if name.endswith(".mastlib") or name.endswith(".zip"):
                    p = os.path.join(root, name)
                    #DEBUG(p)
                    addons.append(p)
        #
        # look in the story.json
        #
        is_test = sys.modules.get('script')
        if is_test is None or isinstance(is_test, str):
            return []

        script_dir = fs.get_script_dir()
        missions_dir = fs.get_missions_dir()
        story_settings = os.path.join(script_dir,"story.json")
        lib_dir = os.path.join(missions_dir,"__lib__")
        if not os.path.exists(story_settings):
            return []
        with open(story_settings, 'r') as file:
            data = json.load(file)
            # No file that's OK
            if data is None:
                return addons
            mastlibs = data.get("mastlib", [])
            for file in mastlibs:
                f = os.path.join(lib_dir, file)
                addons.append(f)
            
        return addons
    

    def expand_resources(self):
        script_dir = fs.get_script_dir()
        missions_dir = fs.get_missions_dir()
        story_settings = os.path.join(script_dir,"story.json")
        lib_dir = os.path.join(missions_dir,"__lib__")
        if not os.path.exists(story_settings):
            return
        with open(story_settings, 'r') as file:
            data = json.load(file)
            res_zips = data.get("resources", {})
            for folder, zip_name in res_zips.items():
                z = os.path.join(lib_dir, zip_name)
                f = os.path.join(script_dir, folder)
                fs.expand_zip(z, f)
                
        

            
    def from_file(self, file_name, root):
        """ Docstring"""
        if root is None:
            root = self # I am root
            #
            # Expand any dependant resources
            #
            self.expand_resources()

        if self.lib_name is None and root.imported.get(file_name):
            return
        elif self.lib_name is not None and root.imported.get(f"{self.lib_name}::{file_name}"):
            return
        
        if self.lib_name is None:
            root.imported[file_name] = True
        else: 
            root.imported[f"{self.lib_name}::{file_name}"] = True

        content = None
        errors= None


        content, errors = self.content_from_lib_or_file(file_name)
      
        if errors is not None:
            return errors
        if content is not None:
            content = content.replace("\r","")
            errors = self.compile(content, file_name, root)

                
            if len(errors) == 0 and not self.is_import:
                addons = self.find_add_ons(".")
                for name in addons:
                    errors = self.import_content("__init__.mast", root, name)
                    if len(errors)>0:
                        return errors

                imports = self.find_imports(".")
                for name in imports:
                    errors = self.import_content(name, root, None)
                    if len(errors)>0:
                        return errors
                    

        return errors
            

        return []
        

    def content_from_lib_or_file(self, file_name):
        try:
            if self.lib_name is not None:
                lib_name = self.lib_name
                if ":" not in self.lib_name:
                    lib_name = os.path.join(fs.get_missions_dir(), self.lib_name)

                with ZipFile(lib_name) as lib_file:
                    #
                    # NOTE: Zip files must use /
                    #
                    if self.basedir is not  None:
                        file_name = os.path.join(self.basedir, file_name).replace("\\", '/')
                    elif self.parent_basedir is not None:
                        file_name = os.path.join(self.parent_basedir, file_name).replace("\\", '/')

                    with lib_file.open(file_name) as f:
                        DEBUG(f"DEBUG: {self.lib_name} {file_name}")
                        content = f.read().decode('UTF-8')
                        self.basedir = os.path.dirname(file_name)
                        return content, None

            else:
                og_file_name = file_name
                if self.basedir is not  None:
                    file_name = os.path.join(self.basedir, file_name)
                elif self.parent_basedir is not None:
                    file_name = os.path.join(self.parent_basedir, file_name)
                else:
                    file_name = os.path.join(fs.get_mission_dir(), file_name)
                # if not found in the basedir or parent basedir
                if not os.path.isfile(file_name):
                    file_name = os.path.join(fs.get_mission_dir(), og_file_name)

                self.basedir = os.path.dirname(file_name)
                    
                with open(file_name) as f:
                    content = f.read()
                return content, None
        except:
            if self.lib_name is not None:
                message = f"File load error\nCannot load file {file_name} from library {self.lib_name}"
            else:
                message = f"File load error\nCannot load file {file_name}"
            return None, [message]
            
        
    

    def import_content(self, filename, root, lib_name):
        add = self.__class__(is_import=True)
        add.parent_basedir = self.basedir
        #
        # Only the nest file needs to know about 
        # lib name
        #
        if self.lib_name is not None:
            add.lib_name = self.lib_name
        elif lib_name is not None:
            add.lib_name = lib_name
            add.parent_basedir = None

        # add.is_import = True
        errors = add.from_file(filename, root)
        if len(errors)==0:
            for label, node in add.labels.items():
                if label != "main":
                    self.labels[label] = node
        return errors


    def compile(self, lines, file_name, root):
        # Catching compiler errors lower to give better error message
        errors = []
        try:
            return self._compile(lines, file_name, root)
        except Exception as e:
            logger = logging.getLogger("mast.compile")
            logger.error(f"Exception: {e}")
            errors.append(f"\nException: {e}")
            errors.append(format_exception("",""))
            return errors # return with first errors

        

    def _compile(self, lines, file_name, root):
        file_num = self.clear(file_name, root)
        line_no = 1 # file line num are 1 based
        
        errors = []
        main = self.labels.get("main")
        if root is not None:
            main = root.labels.get("main", main)
        


        active = main # self.labels.get("main")
        active_name = "main"
        indent_stack = [(0,None)]
        prev_node = None
        label_first_cmd = 0

        class CompileInfo:
            def __init__(self) -> None:
                self.indent = None
                self.is_indent = None
                self.is_dedent = None
                self.label = None
                self.prev_node = None
                self.file_num = None
                
        def buildErrorMessage(file_name, line_no, line, error):
            if line != "":
                line = f"- '{line}'"
            basedir = f"module {self.basedir}"
            if self.lib_name is not None:
                basedir = f"addon {self.lib_name}/{self.basedir}"

            return f"\nError: {error}\nat {file_name} Line {line_no} {line}\n{basedir}\n\n"
        
        def buildExceptionMessage(file_name, line_no, line, error):
            if line != "":
                line = f"- '{line}'"
            basedir = f"module {self.basedir}"
            if self.lib_name is not None:
                basedir = f"addon {self.lib_name}/{self.basedir}"
            
            return f"\nException: {error}\nat {file_name} Line {line_no} {line}\n{basedir}\n\n"

        def inject_dedent(ind_level, indent_node, dedent_node, info):
            if len(indent_stack)==0:
                logger = logging.getLogger("mast.compile")
                error = buildErrorMessage(file_name, line_no,"","Indentation Error")
                logger.error(error )
                errors.append(error)
                return
            
            if ind_level < indent_stack[0][0]:
                logger = logging.getLogger("mast.compile")
                error = buildErrorMessage(file_name,line_no,"","Indentation Error")
                logger.error(error )
                errors.append(error)
                return

            if ind_level == indent_stack[0][0]:
                return
            loc = len(self.cmd_stack[-1].cmds)
            end_obj = indent_node.create_end_node(loc, dedent_node, info)
            if end_obj:
                end_obj.line_num = indent_node.line_num
                end_obj.line = indent_node.line
                end_obj.file_num = file_num
                self.cmd_stack[-1].add_child(end_obj)
                
            

        def inject_remaining_dedents():
            nonlocal indent_stack
            l = indent_stack[::-1]
            for (ind_level, ind_obj) in l:
                info = CompileInfo()
                info.indent = ind_level
                info.is_indent = False
                info.is_dedent = True
                info.main = main # self.labels.get("main")
                inject_dedent(ind_level, ind_obj, None, info)
            indent_stack = [(0,None)]


        while len(lines):
            mo = first_non_whitespace_index(lines)
            line = 0
            line_no += mo[1] if mo is not None else 0
            #line = lines[:mo]
            lines = lines[mo[0]:]
            indent = max((mo[0] - mo[2]) -1,0)
            #Mast.current_indent = indent  # Replaced with compile_info

            #
            # Allow labels to optionally indent?
            #
            if indent != 0 and active is not None and len(active.cmds) <= label_first_cmd:
                indent_stack = [(indent,None)]
         
            # Keep location in file
            parsed = False
            #
            # HANDLE END OF FILE
            #
            if len(lines)==0:
                # Pop out all indents
                inject_remaining_dedents()
                # Let the label generate any commn
                active.generate_label_end_cmds()
                break

            ## 
            # TDO: This has gotten too indented
            #
            try:
                for node_cls in self.__class__.nodes:
                    #mo = node_cls.rule.match(lines)
                    mo = node_cls.parse(lines)
                    if not mo:
                        continue
                    #span = mo.span()
                    data = mo.data

                    line = lines[mo.start:mo.end]
                    lines = lines[mo.end:]

                    line_no += line.count('\n')
                    

                    parsed = True
                    is_indent = False
                    is_dedent = False

                    if node_cls.__name__ != "Comment":
                        (cur_indent, _)  = indent_stack[-1] 
                        if indent > cur_indent:
                            is_indent = True
                            # indent_stack.append(indent)
                        elif indent < cur_indent:
                            is_dedent = True
                    
                    logger = logging.getLogger("mast.compile")
                    logger.debug(f"PARSED: {node_cls.__name__:} {line}")



                    #match node_cls.__name__:
                    # Throw comments and markers away
                    if node_cls.__name__ == "Comment":
                        pass
                    elif node_cls.is_label:
                        _info = CompileInfo()
                        data["compile_info"] = _info
                        next = node_cls(**data)
                        next.file_num = file_num
                        next.line_num = line_no
                        #if active.can_fallthrough() and next.can_fallthrough():
                        if next.can_fallthrough(active):
                            active.next = next
                        else:
                            active.next = None

                        label_name = next.name

                        existing_label = self.labels.get(label_name) 
                        replace = data.get('replace')
                        if existing_label and not replace:
                            parsed = False
                            error = buildErrorMessage(file_name, line_no, line, f"Duplicate label '{label_name }'. Use 'replace: {data['name']}' if this is intentional.")
                            errors.append(error)
                            break
                        elif existing_label and replace:
                            from .core_nodes.jump_cmd import Jump

                            # Make the pervious version jump to the replacement
                            # making fall through also work
                            existing_label.cmds = [Jump(jump_name=label_name,loc=0)]

                        # Close any remain indents
                        inject_remaining_dedents()
                        # THEN
                        # Generate any close block command
                        active.generate_label_end_cmds()
                        #
                        #
                        #
                        from .core_nodes import Await
                        if len(Await.stack)>0:
                            Await.stack.clear()
                        ##
                        ##


                        ## Allow label to generate some preabmle commands
                        active = next
                        active_name = label_name
                        active_name = label_name
                        self.labels[active_name] = active
                        _info = CompileInfo()
                        _info.indent = indent
                        _info.is_dedent = is_dedent
                        _info.is_indent = is_indent
                        _info.label = next
                        _info.main = main # self.labels.get("main")
                        next.generate_label_begin_cmds(_info)
                        label_first_cmd = len(next.cmds)
                        
                        self.labels[active_name] = active
                        exists =  Agent.SHARED.get_inventory_value(label_name)
                        exists =  MastGlobals.globals.get(label_name, exists)
                        if exists and not replace:
                            error = buildErrorMessage(file_name,line_no,line,f"Label conflicts with shared name, rename label '{label_name}'.")
                            errors.append(error)
                            break

                        # Sets a variable for the label
                        Agent.SHARED.set_inventory_value(label_name, active)

                        self.cmd_stack.pop()
                        self.cmd_stack.append(active)
                        prev_node = active

                    
                    elif node_cls.__name__== "Import":
                        lib_name = data.get("lib")
                        name = data['name']

                        if name.endswith('.py'):
                            self.import_python_module_for_source(name, lib_name)
                        elif name.endswith('.zip') or name.endswith('.mastlib'):
                            err = self.import_content("__init__.mast", root, name)
                            if err is not None:
                                errors.extend(err)
                                for e in err:
                                    print("import error "+e)
                        else:
                            err = self.import_content(name, root, lib_name)
                            if err is not None:
                                errors.extend(err)
                                for e in err:
                                    print("import error "+e)
                                    return errors
                        prev_node = None
                    else:
                        try:
                            loc = len(self.cmd_stack[-1].cmds)
                            info = CompileInfo()
                            info.indent = indent
                            info.is_dedent = is_dedent
                            info.is_indent = is_indent
                            info.label=active
                            info.prev_node = prev_node
                            info.main = self.labels.get("main")
                            info.basedir = root.basedir

                            
                            obj = node_cls(compile_info=info,loc=loc, **data)
                            obj.file_num = file_num
                            obj.line_num = line_no

                        except Exception as e:
                            logger = logging.getLogger("mast.compile")
                            error = buildExceptionMessage(file_name, line_no,line,f"{e}")
                            logger.error(error)
                            logger.error(f"Exception: {e}")

                            errors.append(error)
                            errors.append(f"\nException: {e}")
                            return errors # return with first errors

                        obj.line = line if Mast.include_code else None
                        base_indent= indent_stack[0][0]
                        if obj.never_indent() and indent>base_indent:
                            errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                            return errors # return with first errors
                        
                        if not is_indent:
                            if prev_node is not None and prev_node.must_indent():
                                errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                                return errors # return with first errors
                        if is_indent:
                            if prev_node is None or not prev_node.is_indentable():
                                if not prev_node.is_inline_label:
                                    errors.append(buildErrorMessage(file_name,line_no,line,"Bad indentation"))
                                    return errors # return with first errors
                            block_node = prev_node
                            indent_stack.append((indent,block_node))
                        if is_dedent:
                            if len(indent_stack)==0:
                                errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                                return errors # return with first errors
                            
                            (i_loc,_) = indent_stack[-1]
                            while i_loc > indent:
                                if len(indent_stack)==1 and obj.is_inline_label:
                                    break

                                (i_loc,i_obj) = indent_stack.pop()
                                if len(indent_stack)==0:
                                    errors.append(buildErrorMessage(file_name, line_no,line,"Bad indentation"))
                                    return errors # return with first errors

                                # Should equal i_obj
                                end_obj = i_obj.create_end_node(loc, obj,info)
                                #
                                # So far only loops need this
                                # Creates the end node
                                #
                                if end_obj:
                                    self.cmd_stack[-1].add_child(end_obj)
                                    loc+=1
                                    end_obj.file_num = file_num
                                    end_obj.line_num = line_no
                                    end_obj.line = obj.line
                                    obj.loc += 1
                                
                                (i_loc,_) = indent_stack[-1]
                        #
                        # This is for nesting things
                        # like for loops, that should wait to do things 
                        #
                        obj.post_dedent(info)
                        self.cmd_stack[-1].add_child(obj)
                        if not obj.is_virtual():
                            prev_node = obj
                    break
            except Exception as e:
                logger = logging.getLogger("mast.compile")
                error = buildExceptionMessage(file_name, line_no,line,f"{e}")
                logger.error(error)
                logger.error(f"Exception: {e}")

                errors.append(error)
                errors.append(f"\nException: {e}")
                return errors # return with first errors


            if not parsed:
                mo = first_non_newline_index(lines)

                if mo:
                    # this just blank lines
                    #line_no += mo
                    line = lines[:mo]
                    lines = lines[mo:]
                else:
                    mo = first_newline_index(lines)

                    logger = logging.getLogger("mast.compile")
                    error = buildErrorMessage(file_name, line_no, "", "Error at first newline index")
                    logger.error(error )
                    errors.append(error)
                    lines = lines[mo+1:]

        # from .core_nodes import Await
        # for node in Await.stack:
        #     errors.append(f"\nERROR: Missing end_await prior to label '{active_name}'cmd {node.loc}")
        # Await.stack.clear()
        # from .core_nodes import LoopStart
        # for node in LoopStart.loop_stack:
        #     errors.append(f"\nERROR: Missing next of loop prior to label''{active_name}'")
        # LoopStart.loop_stack.clear()
        # for node in IfStatements.if_chains:
        #     errors.append(f"\nERROR: Missing end_if prior to label '{active_name}'cmd {node.loc}")
        # IfStatements.if_chains.clear()
        # for node in MatchStatements.chains:
        #     errors.append(f"\nERROR: Missing end_match prior to label '{active_name}'cmd {node.loc}")
        # MatchStatements.chains.clear()
        return errors

    def enable_logging():
        logger = logging.getLogger("mast")
        handler  = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s|%(name)s|%(message)s"))
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        # fh = logging.FileHandler('mast.log')
        # fh.setLevel(logging.DEBUG)
        # logger.addHandler(fh)

