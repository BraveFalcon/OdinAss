from functools import partial
from typing import List, Callable, Tuple, Optional
from itertools import chain
from functools import wraps


class Route:
    def __init__(self, func: Callable, name: str, description: str = None, help: str = None, aliases: List[str] = None):
        if description is None:
            description = ""
        if help is None:
            help = ""
        if aliases is None:
            aliases = []

        self.name = name
        self.description = description
        self.help = help
        self.aliases = aliases
        self.func = func
    
    def __set_name__(self, owner, _):
        # register route in user
        owner.routes.append(self)
    
    def __get__(self, obj, cls):
        # AAAAAAAAAA
        # bound method emulation
        class BoundRoute:
            def __init__(self, obj, route: Route):
                object.__setattr__(self, 'obj', obj)
                object.__setattr__(self, 'route', route)
            
            def __call__(self, *args, **kwargs):
                return self.func(object.__getattribute__(self, 'obj'), *args, **kwargs)
            
            def __getattr__(self, attr):
                return getattr(object.__getattribute__(self, 'route'), attr)
            
            def __setattr__(self, attr, value):
                return setattr(object.__getattribute__(self, 'route'), attr, value)
        
        return BoundRoute(obj, self)

    def __repr__(self):
        return  "Route {{ name = {name}, description = {description}, help = {help}, aliases = {aliases} }}".format(self.__dict__)


@wraps(Route)
def route(*args, **kwargs):
    return partial(Route, *args, **kwargs)


class Router:
    routes: List[Route] = []
    
    def find_route(self, line: str) -> Optional[Tuple[Route, str]]:
        '''
        Checks if line starts with any of known routes
        Returns: route and rest of the line if found, None otherwise
        '''
        
        low = line.lower()
        for route in self.routes:
            for variant in chain([route.name], route.aliases):
                if low.startswith(variant):
                    return route, line[len(variant):].strip()
        