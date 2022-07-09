import toml
import json
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

import os
from odoo_tools.cli.odot import command
# from odoo_tools.cli import fetch_addons, copy_addons


@pytest.fixture
def runner():
    return CliRunner()


def test_command():
    with pytest.raises(SystemExit):
        command()


def test_shell(runner):
    with patch('ptpython.repl.embed') as mocked_func:
        mocked_func.return_value = 10
        result = runner.invoke(command, ["shell", "testdb"])
        msg = "Odoo doesn't seem to be installed.\n"
        assert isinstance(result.exception, SystemExit)
        assert result.output == msg


def test_list_modules(runner, tmp_path):
    result = runner.invoke(command, ['module', 'ls'])
    assert not result.exception
    assert result.output == ""


def test_list_modules2(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True)

    result = runner.invoke(
        command,
        ['module', 'ls', '--only-name'],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )

    assert not result.exception
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == {'a', 'b', 'c', 'd'}

    extra_addons = tmp_path / 'addons2'
    extra_addons.mkdir()
    generate_addons(extra_addons, ['e'], server_wide=True)

    # Exclude odoo should remove all addons in odoo_dir
    result = runner.invoke(
        command,
        [
            '--exclude-odoo',
            'module', 'ls', '--only-name'
        ],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == set()

    # Exclude odoo should remove all addons in odoo_dir
    # but include custom paths
    result = runner.invoke(
        command,
        [
            '--exclude-odoo',
            'module', 'ls', '--only-name'
        ],
        env={
            'ODOO_BASE_PATH': str(odoo_dir),
            'ODOO_EXTRA_PATHS': str(extra_addons),
        }
    )
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == set(['e'])


def test_list_modules_installable(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True, installable=False)

    result = runner.invoke(
        command,
        ['module', 'ls', '--only-name', '--installable'],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )

    assert not result.exception
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == {'a', 'b', 'c'}

    result = runner.invoke(
        command,
        ['module', 'ls', '--only-name', '--non-installable'],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )

    assert not result.exception
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == {'d'}


def test_list_modules_paths(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])

    result = runner.invoke(command, ['module', 'ls'])
    assert not result.exception
    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'module',
            'ls',
            '-p', str(tmp_path),
            '--sorted',
            '--csv',
            '--only-name',
            # '--without-version',
        ]
    )

    assert result.output == 'a,b,c\n'


def test_list_modules_paths_no_version(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])

    result = runner.invoke(command, ['module', 'ls'])
    assert not result.exception
    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'module',
            'ls',
            '-p', str(tmp_path),
            '--sorted',
            '--csv',
            '--only-name',
            '--without-version',
        ]
    )

    assert result.output == 'a,b,c\n'


def test_list_modules_paths_modules(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])

    result = runner.invoke(command, ['module', 'ls'])
    assert not result.exception
    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'module',
            'ls',
            '-p', str(tmp_path),
            '--sorted',
            '--csv',
            '--only-name',
            '-m', 'a',
            '-m', 'c'
        ]
    )

    assert result.output == 'a,c\n'


def test_show_modules(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True, installable=False)

    result = runner.invoke(
        command,
        ['module', 'show', 'd'],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )

    assert isinstance(result.exception, SystemExit)

    result = runner.invoke(
        command,
        ['module', 'show', 'a'],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )

    expected_data = {
        'application': False,
        'data': [],
        'demo': [],
        'depends': ['web'],
        'description': 'a',
        'external_dependencies': {},
        'installable': True,
        'name': 'a',
        'technical_name': 'a',
        'version': '0.0.0',
    }

    data = json.loads(result.output)
    assert data == expected_data


def generate_odoo_dir(tmp_path):
    odoo_dir = tmp_path / "odoo"
    odoo_dir.mkdir()
    addons_dir = odoo_dir / "addons"
    addons_dir.mkdir()

    return odoo_dir, addons_dir


def generate_addons(addons_dir, modules, **kw):
    for module in modules:
        mod_dir = addons_dir / module
        mod_dir.mkdir()

        manifest = mod_dir / '__manifest__.py'

        with manifest.open('w') as man:
            module_dict = {
                "description": module,
                "depends": ["web"]
            }

            for key, value in kw.items():
                module_dict[key] = value

            man.write(repr(module_dict))


def test_requirements(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True, installable=False)
    generate_addons(
        addons_dir, ['e'], external_dependencies={'python': ['requests']}
    )
    generate_addons(
        addons_dir, ['f'], external_dependencies={'python': ['Pillow']}
    )
    result = runner.invoke(
        command,
        ['module', 'requirements', '--sort'],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )

    assert result.output == "pillow\nrequests\n"


def test_deps(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'], depends=[])
    generate_addons(addons_dir, ['d'], depends=['a'])
    generate_addons(addons_dir, ['e'], depends=['b'])
    generate_addons(addons_dir, ['z'], depends=['c'])
    generate_addons(addons_dir, ['f'], depends=['e', 'd', 'z'])
    generate_addons(addons_dir, ['h'], depends=['b'], auto_install=True)
    generate_addons(addons_dir, ['g'], depends=['f', 'h'], auto_install=True)

    result = runner.invoke(
        command,
        ['module', 'deps', '-m', 'f', '--auto', '--only-name', '--csv'],
        env={'ODOO_BASE_PATH': str(odoo_dir)}
    )

    assert result.output == "a,b,c,d,e,h,z,g"


def test_service(runner, tmp_path):
    services = {
        "services": [
            {
                "name": "base",
                "addons": [
                    {
                        "url": "https://github.com/oca/web.git",
                    },
                    {
                        "url": "self",
                        "branch": "12.0-tests"
                    }
                ]
            },
            {
                "name": "test",
                "inherit": "base",
                "odoo": {
                    "version": "12.0",
                    "repo": {
                        "url": "https://github.com/odoo/odoo.git",
                    }
                },
                "addons": [
                    {
                        "url": "https://github.com/oca/knowledge.git"
                    }
                ]
            }
        ]
    }

    manifest_toml = tmp_path / 'services.toml'

    with manifest_toml.open('w') as fout:
        toml.dump(services, fout)

    result = runner.invoke(
        command,
        [
            'service',
            'show',
            '--url', 'https://github.com/llacroix/addons.git',
            str(manifest_toml),
            "test"
        ],
    )

    assert result.exception is None

    output = json.loads(result.output)

    out_data = {
        "name": "test",
        "odoo": {
            "version": "12.0",
            "repo": {
                "url": "https://github.com/odoo/odoo.git",
                'branch': None,
                'commit': None,
                'private_key': None,
                'ref': '12.0',
            },
            "options": {}
        },
        "env": {},
        "labels": {},
        "addons": {
            "github_com_oca_web": {
                "url": "https://github.com/oca/web.git",
                'branch': None,
                'commit': None,
                'private_key': None,
                'ref': '12.0',
            },
            "github_com_oca_knowledge": {
                "url": "https://github.com/oca/knowledge.git",
                'branch': None,
                'commit': None,
                'private_key': None,
                'ref': '12.0',
            },
            "self": {
                "url": "https://github.com/llacroix/addons.git",
                'branch': "12.0-tests",
                'commit': None,
                'private_key': None,
                'ref': '12.0-tests',
            }
        }
    }

    assert output == out_data


def test_odot_platform(runner, tmp_path):
    result = runner.invoke(
        command,
        [
            'platform',
            'arch'
        ],
    )

    assert result.output == "amd64"


def test_config(env, tmp_path, runner):
    odoo_rc_path = tmp_path / 'odoo.cfg'

    envs = {
        'ODOO_RC': str(odoo_rc_path)
    }

    runner.env = envs

    result = runner.invoke(
        command,
        [
            'config',
            'get',
            'data_dir'
        ],
        env=envs,
    )

    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'config',
            'set',
            'data_dir',
            'value'
        ],
        env=envs,
    )

    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'config',
            'get',
            'data_dir',
        ],
        env=envs,
    )

    assert result.output == "value\n"

    result = runner.invoke(
        command,
        [
            'config',
            'ls',
        ]
    )
    assert result.output == "options.data_dir = value\n"


def test_config_path(runner, tmp_path):
    cfg_path = tmp_path / 'odoo.config'

    with cfg_path.open('w') as fout:
        fout.write("")

    new_vals = {
        'ODOO_RC': str(cfg_path)
    }

    result = runner.invoke(
        command,
        [
            'config',
            'path',
        ],
        env=new_vals
    )

    assert result.output == "{}\n".format(cfg_path)

    result = runner.invoke(
        command,
        [
            '--config', str(cfg_path),
            '--log-level', 'info',
            'config',
            'path',
        ],
    )

    assert result.output == "{}\n".format(cfg_path)


def test_platform(runner):
    with patch('odoo_tools.cli.click.platform.pp') as pp:
        pp.processor.return_value = 'x86_64'
        result = runner.invoke(
            command,
            [
                'platform',
                'arch'
            ],
        )
        assert result.output == "amd64"

        pp.processor.return_value = 'aarch64'
        result = runner.invoke(
            command,
            [
                'platform',
                'arch'
            ],
        )
        assert result.output == "arm64"

        pp.processor.return_value = 'custom'
        result = runner.invoke(
            command,
            [
                'platform',
                'arch'
            ],
        )
        assert result.output == "custom"


def test_path_ls(runner, tmp_path):
    result = runner.invoke(
        command,
        [
            'path',
            'ls'
        ],
    )
    assert result.output == ""


def test_path_ls_modules(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    addons_dir2 = tmp_path / 'addons2'
    addons_dir2.mkdir()
    addons_dir3 = tmp_path / 'addons3'
    addons_dir3.mkdir()
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True)
    generate_addons(addons_dir2, ['f'], server_wide=True)
    generate_addons(addons_dir3, ['e'], server_wide=True)

    result = runner.invoke(
        command,
        [
            'path',
            'ls'
        ],
    )
    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'path',
            'ls'
        ],
        env={
            'ODOO_BASE_PATH': str(odoo_dir)
        }
    )
    assert result.output == "{}\n".format(str(addons_dir))

    result = runner.invoke(
        command,
        [
            '--exclude-odoo',
            'path',
            'ls',
            '--sorted',
        ],
        env={
            'ODOO_BASE_PATH': str(odoo_dir),
            'ODOO_EXTRA_PATHS': str(tmp_path),
        }
    )
    assert result.output == "{}\n{}\n".format(
        str(addons_dir2),
        str(addons_dir3),
    )

    result = runner.invoke(
        command,
        [
            'path',
            'ls',
            '--sorted',
        ],
        env={
            'ODOO_BASE_PATH': str(odoo_dir),
            'ODOO_EXTRA_PATHS': str(tmp_path),
        }
    )
    assert result.output == "{}\n{}\n{}\n".format(
       str(addons_dir2),
       str(addons_dir3),
       str(addons_dir),
    )

    result = runner.invoke(
        command,
        [
            'path',
            'ls',
            '--sorted',
            str(tmp_path),
        ],
        env={
            'ODOO_BASE_PATH': str(odoo_dir),
        }
    )
    assert result.output == "{}\n{}\n{}\n".format(
       str(addons_dir2),
       str(addons_dir3),
       str(addons_dir),
    )


def test_path_set_get(runner, tmp_path):
    config = tmp_path / 'odoo.cfg'
    with config.open('w') as fout:
        fout.write("")

    # Does nothing as there are no modules in paths
    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'add',
            str(tmp_path)
        ]
    )

    assert result.exception is None

    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'ls',
        ]
    )

    assert result.output == ""

    addons_path = tmp_path / 'a' / 'b'
    addons_path.mkdir(parents=True)
    generate_addons(addons_path, ['a', 'b', 'c'])

    addons_path2 = tmp_path / 'd'
    addons_path2.mkdir(parents=True)
    generate_addons(addons_path2, ['d', 'e', 'f'])

    # Should add the new addons path subdirectory
    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'add',
            str(tmp_path / 'a')
        ]
    )

    assert result.exception is None

    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'ls',
        ]
    )

    assert result.output == "{}\n".format(addons_path)

    # Should add the new addons path subdirectory
    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'add',
            str(tmp_path / 'd')
        ]
    )

    assert result.exception is None

    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'ls',
            '--sorted',
        ]
    )

    assert result.output == "{}\n{}\n".format(
        addons_path,
        addons_path2,
    )

    # Should add the new addons path subdirectory
    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'rm',
            str(tmp_path / 'd')
        ]
    )

    assert result.exception is None

    result = runner.invoke(
        command,
        [
            '-c', str(config),
            'path',
            'ls',
            '--sorted',
        ]
    )

    assert result.output == "{}\n".format(
        addons_path,
    )
