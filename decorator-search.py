#!/usr/bin/env python3

import argparse
import os
import ast

"""
  Search functions by decorators (and function names if you need to!)

"""

"""
Nice for structure and memory use (do we really care? How much Python are we parsing?!) :
{
  "a/b/c/d.py": {
    "class": "name",
    "functions":[
      {
        "name": "func1",
        "line": 123,
        "decorators": [
          {
            "name": "dec_name",
            "value", "123"
        ]
      }
    ]
  }
}
  
----

Better for easy search (especially for writing the actual lambdas!) :

[
  {"path": "a/b/c/d.py", "class": "name", "function": "func1", "line": 123, "decorators": [ ...] },
  {"path": "a/b/c/d.py", "class": "name2", "function": "func2", "line": 223, "decorators": [ ...] },
  ...
]
"""

# ====================================================================================================

class DecoratorSearcher(object):
    def __init__(self):
        self.results = []
        self.ignore = []

# ----------------------------------------------------------------------------------------------------
    def start(self, args):
        self.ignore = args.ignore
        self.parse_folder(args.folder)

# ----------------------------------------------------------------------------------------------------
        
    def parse_folder(self, folder):
        with os.scandir(folder) as f:
            for path in f:
                if path.name in self.ignore:
                    continue
                if path.is_dir():
                    self.parse_folder(path.path)
                elif path.is_file() and path.name.endswith('.py'):
                    #print(f'[*] Parsing {path.path}')
                    m = Module()
                    self.results.extend(m.load(path.path))

# ----------------------------------------------------------------------------------------------------

    def from_results(self, results):
        self.results = results

# ----------------------------------------------------------------------------------------------------

    def add_results(self, results):
        self.results.extend(results)

# ----------------------------------------------------------------------------------------------------

    def pretty(self):
        for entry in self.results:
            print(f'{entry.path}:{entry.line}')
            print('\n'.join([f'@{dec.name}({dec.value})' for dec in entry.decorators]))
            print(f'  {entry.class_name}:{entry.function}\n--')

# ----------------------------------------------------------------------------------------------------

    def find(self, callback):
        results = []
        for entry in self.results:
            if callback(entry):
                results.append(entry)
        # build a new object and return it!
        # we can use this to chain queries like "find functions with decorator X then filter those that don't have decorator Y"
        results_object = DecoratorSearcher()
        results_object.from_results(results)
        return results_object

# ----------------------------------------------------------------------------------------------------

    """
    *Only* searches decorators!
    Keeps things simple, but limits our flexibility
    If one decorator matches we add the result to our result set
    """
    def findAny(self, callback):
        results = []
        for entry in self.results:
            for decorator in entry['decorators']:
                if type(decorator) != ObjDict:
                    print('NOT DICT!')
                    print(decorator)
                    continue
                if callback(decorator):
                    results.append(entry)
                    break

        # build a new object and return it!
        # we can use this to chain queries like "find functions with decorator X then filter those that don't have decorator Y"
        results_object = DecoratorSearcher()
        results_object.from_results(results)
        return results_object

# ----------------------------------------------------------------------------------------------------

    """
    *Only* searches decorators!
    Keeps things simple, but limits our flexibility
    If all decorators match we add the result to our result set
    Useful for negative searches
    """
    def findAll(self, callback):
        results = []
        for entry in self.results:
            hit = True
            for decorator in entry['decorators']:
                if not callback(decorator):
                    hit = False
                    break
            if hit:
                results.append(entry)
 
        # build a new object and return it!
        # we can use this to chain queries like "find functions with decorator X then filter those that don't have decorator Y"
        results_object = DecoratorSearcher()
        results_object.from_results(results)
        return results_object

# ----------------------------------------------------------------------------------------------------

    """
    Searches by partial name match:
    name: a_decorator_name
    
    dec => matches
    a_decorator_name2 => does NOT match
    """
    def find_decorators_by_name(self, name):
        return self.findAny(lambda d: name in d.name)

# ----------------------------------------------------------------------------------------------------

    """
    Searches by partial name match:
    name: a_decorator_name
    
    dec => matches
    a_decorator_name2 => does NOT match
    """
    def find_decorators_by_exact_name(self, name):
        return self.findAny(lambda d: d.name == name)

# ----------------------------------------------------------------------------------------------------

    """
    Searches by partial value match:
    value: /users/(?P<accountType>\\w+)-(?P<userID>\\d+)/assets/products/$
    
    users => matches
    /Users => does NOT match
    """
    def find_decorators_by_value(self, value):
        return self.findAny(lambda d: value in d.value)

# ----------------------------------------------------------------------------------------------------

    """
    Searches by partial value match:
    value: /users/(?P<accountType>\\w+)-(?P<userID>\\d+)/assets/products/$
    
    users => matches
    /Users => does NOT match
    """
    def find_decorators_by_exact_value(self, value):
        return self.findAny(lambda d: d['value'] == value)

# ----------------------------------------------------------------------------------------------------

    """
    Exact match on both decorator and value
    """
    def find_decorators_by_name_and_value(self, name, value):
        return self.find(lambda d: name in d.name and value in d.value)


# ====================================================================================================
# Parses a single Python file
# ====================================================================================================

class Module(object):
    def __init__(self):
        self.results = []
        self._tree = None

# ----------------------------------------------------------------------------------------------------

    def from_results(self, results):
        self.results = results

# ----------------------------------------------------------------------------------------------------

    def load(self, path):
        with open(path, 'r') as fd:
            self._tree = ast.parse(fd.read())
        self.parse(path)
        return self.results

# ----------------------------------------------------------------------------------------------------

    def parse(self, path):
        for node in self._tree.body:
            match type(node):
                case ast.ClassDef:
                    self.parse_class(node, path)
                # case FunctionDef: *** should we be looking for module level functions too?...

# ----------------------------------------------------------------------------------------------------

    def parse_class(self, cls_node, path):
        functions = []
        for node in cls_node.body:
            match type(node):
                case ast.FunctionDef:
                    parsed_func = self.parse_function(node, class_name=cls_node.name, class_decorators=cls_node.decorator_list)
                    parsed_func['path'] = path
                    self.results.append(parsed_func)

# ----------------------------------------------------------------------------------------------------

    def parse_function(self, fun_node, class_name="", class_decorators=[]):
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        """
        Parse an Attribute into 'module.class.thing' format
        """
        def handle_Name(node):
            return node.id

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        def handle_Attribute(node):
            match type(node.value):
                case ast.Attribute:
                    return handle_Attribute(node.value) + [node.attr]
                case ast.Name:
                    return [handle_Name(node.value), node.attr]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        def get_name(part):
            match type(part):
                case ast.Attribute:
                   return '.'.join(handle_Attribute(part))
                case ast.Name:    
                    return part.id
                case _:
                    print('[ERROR] Unknown Call.func type:\n ', type(part))
                    exit()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        def parse_argument(argument):
            match type(argument):
                case ast.Attribute:
                    return f'{argument.attr}={argument.value}'
                case ast.BinOp:
                    parts = []
                    match type(argument.left):
                        case ast.Constant:
                            parts.append(argument.left.value)
                        case ast.List:
                            parts.append(str(argument.left))
                        case ast.Name:
                            parts.append(argument.left.id)
                    match type(argument.right):
                        case ast.Constant:
                            parts.append(argument.right.value)
                        case ast.List:
                            parts.append(str(argument.right))
                        case ast.Name:
                            parts.append(argument.right.id)
                    return ''.join(parts)
                case ast.Constant:
                    return argument.value
                case ast.Name:
                    return argument.id
                case ast.List:
                    #print('LIST: ', len(argument.elts))
                    args_list = []
                    for arg in argument.elts:
                        args_list.append(parse_argument(arg))
                    return args_list
                case ast.Call:
                    match type(argument.func):
                        case ast.Attribute:
                            return f'{argument.func.attr}={argument.func.value}'
                        case ast.Name:
                            return f'{argument.func.id}'
                    #print(argument.func)
                case ast.JoinedStr:
                    parts = []
                    for part in argument.values:
                        match type(part):
                            case ast.Constant:
                                parts.append(part.value)
                            case ast.FormattedValue:
                                #print(part.__dir__())
                                #print(part.value, part.format_spec, part.conversion)
                                parts.append(part.value.id)
                                #print(part.format_spec)
                    return ''.join(parts)
                case _:
                    print(f'[WARNING] [Module.parse_argument] Unknown argument type: {type(argument)}')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

        # glue the class and function decorators together to make searching a bit easier
        # the class decorators come first if we do it like this, which feels a bit more natural
        # it's important that we make a copy of the class decorators! Don't just .extend(...) them otherwise we modify the class, which is bad
        decorators = [d for d in class_decorators]
        decorators.extend(fun_node.decorator_list)
      
        # super simple reconstruction of the decorators so we can do a dirty grep
        # TODO - fix this filthy hack!
        decorators_parsed = []
        for decorator in decorators:
            arguments = []

            match type(decorator):
                case ast.Attribute:
                    decorator_name = get_name(decorator)
                    decorator_value = ast.unparse(decorator)[len(decorator_name)+1:-1]
                    decorators_parsed.append(ObjDict({'name':decorator_name, 'value': decorator_value}))
                case ast.Call:
                    decorator_name = get_name(decorator.func)
                    decorator_value = ast.unparse(decorator)[len(decorator_name)+1:-1]
                    decorators_parsed.append(ObjDict({'name':decorator_name, 'value': decorator_value}))
                case ast.Name:
                    decorator_name = get_name(decorator)
                    decorators_parsed.append(ObjDict({'name':decorator_name, 'value': ''}))
                case _:
                    print('[ERROR] Unknown decorator type: ', type(decorator))

        return ObjDict({'class_name':class_name, 'function':fun_node.name, 'line':fun_node.lineno, 'decorators':decorators_parsed})

# ====================================================================================================

class ObjDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


# ====================================================================================================

def instructions():
    print("""
[Python Decorator Search]

Schema:
=======

Function:   {"path": "a/b/c/d.py", "class_name": "name", "function": "func1", "line": 123, "decorators": [ ...] }
Decorator:  {"name": "decorator_name", "value": "b2b"}

Usage:
======

Start from the `ds` object - the following methods are available:

* findAny(lambda d: ...)
* findAll(lambda d: ...)
* find(lambda f: ...)

findAny(lambda d: ...)

 Likely to be the workhorse - if *any* decorator on a function matches, the function will be added to the result set

findAll(lambda d: ...)

 Useful for negative searches, i.e. where you want *all* decorators to not include something. Functions will only be added to the result set if all decorators match

find(lambda f: ...)

 A bit more powerful, but less useful in an interactive lambda. More useful if you add helper functions into the session. Gives you access to the function record, which has things like function and class name, source file path etc.
 
Chaining Queries
================

You can chain queries by simply appending `.findAny(...)` etc. Each query returns a new DirectorySearcher object with the relevant results in it

Display Results
===============

`.pretty()` will print the matched functions in a reasonably sane way including file path and line number, all decorators on the function etc.

`.results` is just the list of results (each entry is a dict)

Examples
========

Find any functions that have a decorator with 'auth' in the name:
>> ds.findAny(lambda d: 'auth' in d.name).pretty()

Find any functions with 'auth' in a decorator name, and 'admin' in the same decorator's value:
>> ds.findAny(lambda d: 'auth' in d.name and 'admin' in d.value).pretty()

Find any functions with 'admin' in a decorator's name, and do not have 'test' in any decorator's name:
>> ds.findAny(lambda d: 'auth' in d.name).findAll(lambda d: 'test' not in d.name).pretty()

""")


def main():
    parser = argparse.ArgumentParser(description='Search Python code by decorators')
    parser.add_argument('folder', type=str, help='Folder to recursively load and parse .py files from')
    parser.add_argument('--ignore', type=str, action='append', help='ignore files and folders with this exact name')
    parser.add_argument('--quiet', action='store_true', help='Disable instructions on start')

    args = parser.parse_args()

    ds = DecoratorSearcher()
    ds.start(args)

    if not args.quiet:
        instructions()

    import IPython
    IPython.embed()


if __name__ == '__main__':
    main()


