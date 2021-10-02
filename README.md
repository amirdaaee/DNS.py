# DNS.py
** DNS.py is a python asyncio based DNS proxy server running on plugins!**

DNS.py can be used as:
- simple dns logger
- Authoritative/Recursive DNS server
- smart DNS server
-  or whatever you need [writing your own plugin]!

## Installation
```bash
git https://github.com/amirdaaee/DNS.py.git
cd DNS.py
pip install -r ./requirements.txt
```
or wait untill `build.py` is pushed

## Usage
`python Server.py --help` will give you almost anything you need to config and run server.
DNS.py is completely dependent on environmental variables for configuration, or you can assign them in `.env` file in project root diretory.
`python Server.py --list-env` gives a list of available configuration variables.

## Plugins
`python Server.py --list-env` gives a list of available plugins. you can activate them using environmental variables.
### writing you own plugins
to create a plugin for your own:
1. create a python file in `Plugins` directory. we call this file **plugin module**
2. define a dict named `CONFIG` in plugin module. this can be used to read custom environmental variables for configuration of plugin. DNS.py uses [pydantic](https://pydantic-docs.helpmanual.io/ "pydantic") for settings management. this defined dict will be used for dynamic model fields in pydantic model. read more about [dynamic model creation](https://pydantic-docs.helpmanual.io/usage/models/#dynamic-model-creation "dynamic model creation") to find out how this dict should be properly defined: `name:(type,default_value)`. these coniguration variables will be available to all plugins defined in the module
3. create a class inheriting from `Plugins.Base.BasePlugin`. note that class name should not start with a `_` otherwise DNS.py won't discover it! we call this class **plugin class**
4. you can add a `CONFIG` varable just like step 2 inside plugin class definition. Unlike module level CONFIG, this variables are just avaiable in this plugins class
5. you can override ` __init__(self, *args, **kwargs)`, but don't forget to initiate super class afterward. see `Plugins.Base.BasePlugin.__doc__` for more information
6. define one of the two (or both) methods `before_resolve` or `after_resolve` in plugin class. this can be a formal function or awaitable. `before_resolve` runs before upstream resolve and `after_resolve` runs afterward. see `before_resolve.__doc__`, `after_resolve.__doc__`, [this](https://dnspython.readthedocs.io/en/stable/rdata.html "this") and [this](https://dnspython.readthedocs.io/en/stable/message.html "this") for more information. how to manipulate them. note that this method should return both question and response objects. you can add in/remove from/edit rrset from both question and response messages to be returned to client
7. `Plugins.Base.BasePlugin.config` gives you module level [no.2] and class level [no.4] configuration data


## Todo
- [ ] completing readme document for plugins
- [ ] completing readme document docker



## Contributing
Pull requests are highly welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.
