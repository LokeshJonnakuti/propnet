import numpy as np

from os import path
from enum import Enum
from io import StringIO
from json import dumps

from pybtex.database.input.bibtex import Parser
from pybtex.plugin import find_plugin
from pybtex.style.labels import BaseLabelStyle

from propnet.symbols import DEFAULT_SYMBOL_TYPE_NAMES, Symbol
from propnet.models import DEFAULT_MODEL_NAMES

from monty.serialization import loadfn

AESTHETICS = loadfn(path.join(path.dirname(__file__), 'aesthetics.yaml'))

def graph_conversion(graph,
                     nodes_to_highlight_green=(),
                     nodes_to_highlight_yellow=(),
                     nodes_to_highlight_red=(),
                     hide_unconnected_nodes=True,
                     aesthetics=None):
    """Utility function to render a networkx graph
    from Graph.graph for use in GraphComponent

    Args:
      graph: from Graph.graph

    Returns: graph dict
    """

    aesthetics = aesthetics or AESTHETICS

    nodes = []
    edges = []

    for n in graph.nodes():

        id = None

        if n.node_type.name == 'Symbol':
            # property
            id = n.node_value.name
            label = n.node_value.display_names[0]
        elif n.node_type.name == 'Model':
            # model
            id = n.node_value.__class__.__name__
            label = n.node_value.title
        #elif n.node_type.name == 'Quantity':
        #    pass
        #elif n.node_type.name == 'Material':
        #    pass

        if id:

            node = AESTHETICS['node_aesthetics'][n.node_type.name].copy()

            if n.node_type.name == 'Symbol' and \
                    AESTHETICS['node_options']['show_symbol_labels']:
                node['label'] = label
            if n.node_type.name == 'Model' and \
                    AESTHETICS['node_options']['show_model_labels']:
                node['label'] = label

            node['id'] = id
            node['title'] = label

            nodes.append(node)

    if nodes_to_highlight_green or nodes_to_highlight_yellow or nodes_to_highlight_red:
        for node in nodes:
            if node['id'] in nodes_to_highlight_green:
                node['fill'] = '#9CDC90'
            elif node['id'] in nodes_to_highlight_yellow:
                node['fill'] = '#FFBF00'
            elif node['id'] in nodes_to_highlight_red:
                node['fill'] = '#FD9998'
            else:
                node['fill'] = '#BDBDBD'

    connected_nodes = set()
    for n1, n2 in graph.edges():

        id_n1 = None
        if n1.node_type.name == 'Symbol':
            id_n1 = n1.node_value.name
        elif n1.node_type.name == 'Model':
            id_n1 = n1.node_value.__class__.__name__

        id_n2 = None
        if n2.node_type.name == 'Symbol':
            id_n2 = n2.node_value.name
        elif n2.node_type.name == 'Model':
            id_n2 = n2.node_value.__class__.__name__

        if id_n1 and id_n2:
            connected_nodes.add(id_n1)
            connected_nodes.add(id_n2)
            edges.append({
                'from': id_n1,
                'to': id_n2
            })

    if hide_unconnected_nodes:
        for node in nodes:
            if node['id'] not in connected_nodes:
                node['hidden'] = True

    graph_data = {
        'nodes': nodes,
        'edges': edges
    }

    return graph_data


def references_to_markdown(references):
    """Utility function to convert a BibTeX string containing
    references into a Markdown string.

    Args:
      references: BibTeX string

    Returns:
      Markdown string

    """

    pybtex_style = find_plugin('pybtex.style.formatting', 'plain')()
    pybtex_md_backend = find_plugin('pybtex.backends', 'markdown')
    pybtex_parser = Parser()

    # hack to not print labels (may remove this later)
    def write_entry(self, key, label, text):
        """

        Args:
          key: 
          label: 
          text: 

        Returns:

        """
        self.output(u'%s  \n' % text)
    pybtex_md_backend.write_entry = write_entry
    pybtex_md_backend = pybtex_md_backend()

    data = pybtex_parser.parse_stream(StringIO(references))
    data_formatted = pybtex_style.format_entries(data.entries.itervalues())
    output = StringIO()
    pybtex_md_backend.write_to_stream(data_formatted, output)

    # add blockquote style
    references_md = '> {}'.format(output.getvalue())
    references_md.replace('\n', '\n> ')

    return references_md

def uri_to_breadcrumb_layout(uri):
    """

    Args:
      uri: return:

    Returns:

    """
    return


def parse_path(pathname):
    """Utility function to parse URL path for routing purposes etc.
    This function exists because the path has to be parsed in
    a few places for callbacks.

    Args:
      path: path from URL
      pathname: 

    Returns:
      dictionary containing 'mode' ('property', 'model' etc.),
      'value' (name of property etc.)

    """

    if pathname == '/' or pathname is None:
        return None

    mode = None  # 'property' or 'model'
    value = None  # property name / model name

    if pathname == '/model':
        mode = 'model'
    elif pathname.startswith('/model'):
        mode = 'model'
        for model in DEFAULT_MODEL_NAMES:
            if pathname.startswith('/model/{}'.format(model)):
                value = model
    elif pathname == '/property':
        mode = 'property'
    elif pathname.startswith('/property'):
        mode = 'property'
        for property in DEFAULT_SYMBOL_TYPE_NAMES:
            if pathname.startswith('/property/{}'.format(property)):
                value = property
    elif pathname == '/load_material':
        mode = 'load_material'
    elif pathname.startswith('/load_material'):
        mode = 'load_material'
        value = pathname.split('/')[-1]
    elif pathname.startswith('/graph'):
        mode = 'graph'

    return {
        'mode': mode,
        'value': value
    }
