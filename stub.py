import sys, inspect, enum,  os



class GenStubs:
    def __init__(self):
        self.file = open('readme.pyi', 'w')
        self._indent = 0
        self.files = []
        
        script_dir = os.path.dirname(__file__).replace("/", "\\")
        self.dirs = script_dir.split("\\")
        self.dirs.append("typings")
        self.debug = False

    def push_file(self, file):
        self.files.append(self.file)
        self.file = file

    def pop_file(self):
        self.file.close()
        self.file = self.files.pop()

    def push_dir(self, dirname):
        self.dirs.append(dirname)

    def pop_dir(self):
        self.dirs.pop()

    def make_file(self, module, name):
        make_dir = False
        
        try:
            if module.__file__ is not None:
                file_base = os.path.basename(module.__file__)
                if file_base == "__init__.py":
                    make_dir = True
            else:
                make_dir = True
                file_base = "__init__.py"
        except:
            make_dir = True
            file_base = "__init__.py"

        if make_dir:
            self.push_dir(name)
        

        full_dir = "\\".join(self.dirs)
        full_file = os.path.join(full_dir, f"{file_base}i")
        
        # 
        if make_dir:
            #self.write(f"##### MKDIR: {full_dir}")
            os.makedirs(full_dir, exist_ok=True)

        self.trace_line(f"##### FILE: {full_file}")
        file = open(full_file, "w")
        #file = None


        return (make_dir, file)


    def trace_line(self, s):
        if self.debug:
            self.write_line(s)

    def trace(self, s):
        if self.debug:
            self.write(s)

    def write_line(self, s):
        lines = s.split('\n')
        for line in lines:
            self.file.write('    '*self._indent)
            self.file.write(f"{line.rstrip()}\n")

    def write(self, s):
        self.file.write(s)

    def indent(self):
        self._indent += 1

    def outdent(self):
        self._indent -= 1
        if self._indent < 0:
            self._indent = 0


    def stub_class(self, cls, name):
        mro = cls.__bases__
        self.write(f"class {name}(")
        comma = False
        pybind = False

        for base in mro:
            if comma:
                self.write(f", ")
            base = base.__name__
            if base.startswith("pybind"):
                base = "object"
                pybind = True
            self.write(f"{base}")
            comma = True
            
        if pybind:
            self.write_line(f"): ### from pybind")
        else:
            self.write_line(f"):")
        
        self.indent()
        self.docstring(cls, f'"""class {name}"""')
        
        in_enum = False
        
        for name, obj in inspect.getmembers(cls):
            ### Try skipping if not override
            skip = False
            if hasattr(cls, "__bases__") and hasattr(cls, name):
                a = getattr(cls, name)
                for base in cls.__bases__:
                    if hasattr(base, name):
                        b = getattr(base, name)
                        if a == b:
                            skip = True
            if skip:
                continue
            
            if inspect.isclass(cls) and isinstance(obj, cls):
                self.stub_enum_value(obj, name)
                in_enum = True
            elif in_enum:
                continue
            elif inspect.ismethod(obj):
                self.stub_class_member(obj, name)
            elif inspect.isfunction(obj):
                self.stub_class_member(obj, name)
            # elif inspect.ismodule(cls) and inspect.isclass(obj):
            #     self.stub_class(obj, name)
            elif inspect.isgenerator(obj):
                self.trace_line(f"# GEN {name}")
            elif inspect.isgeneratorfunction(obj):
                self.trace_line(f"# GEN {name}")
            elif inspect.iscoroutine(obj):
                self.trace_line(f"# CORO {name}")
            elif inspect.isabstract(obj):
                self.trace_line(f"# ABST {name}")
            elif inspect.isframe(obj):
                self.trace_line(f"# FRAME {name}")
            elif inspect.iscoroutinefunction(obj):
                self.trace_line(f"# CORO FUNC {name}")
            elif inspect.iscode(obj):
                self.trace_line(f"# CODE {name}")
            elif inspect.isbuiltin(obj):
                self.stub_class_routine(obj,name, False)
            elif inspect.ismemberdescriptor(obj):
                self.trace_line(f"DESC {name}")
            elif inspect.isroutine(obj):
                self.stub_class_routine(obj,name, False)
                
            elif inspect.isgetsetdescriptor(obj):
               # self.write_line(f"# getset DESC {name}")
               self.stub_data_description(obj, name)
            elif inspect.ismethoddescriptor(obj):
                self.trace_line(f"# meth DESC {name}")
            elif inspect.isdatadescriptor(obj):
                self.stub_data_description(obj,name)
            
            else:
                self.trace_line(f"# UNKNOWN {name} {str(type(obj))}")

        self.outdent()

        

    def stub_class_member(self, obj, name):
        self.stub_class_routine(obj,name, False)

        # skip = ["__init_subclass__", "__new__", "__subclasshook__"]
        # if name in skip:
        #     return
        # if not callable(obj):
        #     self.write_line(f"NOT CALLABLE def {name}:")    
        #     return
        # try:
        #     sig = self.get_clean_sig(obj)
        #     self.write_line(f"def {name} {sig}:")
        #     self.indent()
        #     self.docstring(obj)
        #     self.outdent()
        # except:
        #     self.write_line(f"NO SIGNATURE def {name}:")

    def stub_prop_member(self, obj, fsget, name, header):
        if not callable(fsget):
            self.write_line(f"NOT CALLABLE def {name}:")    
            return

        sig = None
        try:
            sig = self.get_clean_sig(fsget)
        except:
            sig = fsget.__doc__.rstrip()

        if sig is None:
            self.write_line(f"PROP NO SIGNATURE def {name}:")

        self.write_line(header)
        self.write_line(f"def {name} {sig}:")
        self.indent()
        self.docstring(obj)
        self.outdent()

    def stub_data_description(self, obj, name):
        skip = ["__weakref__"]
        if name in skip:
            return
        if hasattr(obj, "__dict__"):
            if name not in obj.__dict__:
                return

        ot = type(obj).__name__
        if ot== 'getset_descriptor':
            self.write_line(f"{name} : {ot}")
            self.docstring(obj)
        elif ot == 'property':
            fget = obj.fget
            fset = obj.fset
            if fget is not None:
                self.stub_prop_member(obj, fget, name, "@property")
            if fset is not None:
                self.stub_prop_member(obj, fset, name, f"@{name}.setter")
                
        else:
            self.write_line(f"{name} : {ot}")
            self.docstring(obj)

    def stub_enum_value(self, obj, name):
        self.write_line(f"{name} : {obj.value}")

        
    def get_clean_sig(self, obj):
        sig = str(inspect.signature(obj))
        sig = sig.replace("<built-in function any>", "any")
        sig = sig.replace("<built-in function callable>", "callable")
        sig = sig.replace("Callable", "callable")
        return sig
    
    def stub_class_routine(self, obj, name, indent):
        skip = ["__init_subclass__", "__new__", "__subclasshook__"]
        if name in skip:
            return
                
        if not callable(obj):
            self.write_line(f"NOT CALLABLE def {name}:")    
            return
        try:
            sig = self.get_clean_sig(obj)
            if "/" in sig:
                return
            self.write_line(f"def {name} {sig}:")
            self.indent()
            self.docstring(obj)
            self.outdent()
        except:
            doc = inspect.getdoc(obj)
            if doc is not None:
                line = doc.split("\n")
                if line[0].startswith(name):
                    self.write_line(f"def {line[0]}:")
                    self.indent()
                    self.docstring(obj, skip_first=True)
                    self.outdent()
                    return
                            
            self.write_line(f"def {name}(*argv):")    
            self.indent()
            self.docstring(obj)
            self.outdent()
            


    def docstring(self,obj, default="...", skip_first=False):
        doc = inspect.getdoc(obj)
        if doc is None:
            self.write_line(default)
        else:
            doc = inspect.cleandoc(doc) 
            if skip_first:
                l = doc.split("\n")
                doc = '\n'.join(l[1:])
            doc = doc.lstrip()
            if (len(doc)>0):
                self.write_line(f'"""{doc}"""')
            else:
                self.write_line(f'...')
        

    def stub_func(self, obj, name):
        self.stub_class_routine(obj, name)

        # if not callable(obj):
        #     self.write_line(f"NOT CALLABLE def {name}:")    
        #     return
        # try:
        #     sig = self.get_clean_sig(obj)
        #     self.write_line(f"def {name} {sig}:")
        #     self.indent()
        #     self.docstring(obj)
        #     self.outdent()
        # except:
        #     self.write_line(f"NO SIGNATURE def {name}:")    



    def stub_module(self, module: str):
        self.stub_module_(sys.modules[module])

    def stub_module_(self, module):
        module_short_name = module.__name__.split(".")
        module_short_name = module_short_name[-1]
        make_dir, file = self.make_file(module, module_short_name)
        self.push_file(file)

        # handle modules after
        classes = []
        imports = {}
        modules = []
        builtins = []
        

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and obj.__module__ != module.__name__:
                if not obj.__module__.startswith("_"):
                    imp = imports.get(obj.__module__, [])
                    imp.append( (name, obj) )
                    imports[obj.__module__] = imp
                
            elif inspect.isfunction(obj):
                builtins.append( (name, obj) )
            elif inspect.isclass(obj):
                classes.append( (name, obj) )
            elif inspect.ismodule(obj):
                if obj.__name__.startswith(module.__name__):
                    modules.append((name,obj))
            elif inspect.isbuiltin(obj):
                builtins.append( (name, obj) )
                

        for imp in imports.values():
            for name, obj in imp:
                self.write_line(f"from {obj.__module__} import {name}")    

        for name, obj in builtins:
            self.stub_class_routine(obj, name, True)

        for name, obj in classes:
            self.stub_class(obj, name)

        for name, obj in modules:
            self.stub_module_(obj)


        self.pop_file()

        if make_dir:
            self.pop_dir()




