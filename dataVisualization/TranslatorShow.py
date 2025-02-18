import sys
import os
from dash import Dash, html, Input, Output, callback
import dash_cytoscape as cyto
import webbrowser
from threading import Timer
import requests as r

sys.path.append(os.path.join(os.getcwd()))
print(os.path.join(os.getcwd()))
from dataExtraction import TranslatorExtract
from queries import TranslatorMessages



sys.path.append(os.path.join(os.getcwd()))
print(os.path.join(os.getcwd()))

@callback(Output('click-data', 'children'),
          Input('Translator-cytoscape-fullscreen', 'tapNodeData'),
          Input('Translator-cytoscape-fullscreen', 'tapEdgeData'))

def display_click_data(node_data, edge_data):
    if node_data:
        return html.Table([
            html.Tr([html.Th("Node Info")]),
            html.Tr([html.Td("id"), html.Td(node_data['id'])]),
            html.Tr([html.Td("category"), html.Td(node_data['category'])])
        ])
    elif edge_data:
        return html.Table([
            html.Tr([html.Th("Edge Info")]),
            html.Tr([html.Td("id"), html.Td(edge_data['id'])]),
            html.Tr([html.Td("primary_source"), html.Td(edge_data['primary_source'])]),
            html.Tr([html.Td("ARA"), html.Td(edge_data['ARA'])])
        ])
    return "Click on a node or edge to see additional information"

def update_output_div(input_value):
    return f'Output: {input_value}'

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050")


def cytoscape_layout_setup(elements):
    # USAGE:
    #     elements = [
    #     {'data': {'id': 'one', 'label': 'Node 1'}},
    #     {'data': {'id': 'two', 'label': 'Node 2'}},
    #     {'data': {'source': 'one', 'target': 'two'}}
    # ]
    #  app = cytoscape_layout_setup(elements)
    
    app = Dash(__name__, suppress_callback_exceptions=True)

    app.layout = html.Div([
        cyto.Cytoscape(
            id='Translator-cytoscape-fullscreen',
            layout={'name': 'cose',
            'idealEdgeLength': 100,
            'nodeOverlap': 20,
            'refresh': 20,
            'fit': True,
            'padding': 30,
            'randomize': False,
            'componentSpacing': 100,
            'nodeRepulsion': 400000,
            'edgeElasticity': 100,
            'nestingFactor': 5,
            'gravity': 80,
            'numIter': 1000,
            'initialTemp': 200,
            'coolingFactor': 0.95,
            'minTemp': 1.0},
            style={
                'width': '100%',
                'height': 'calc(100vh - 0px)'
            },
            elements=elements
        )
    ])
    return app



if __name__ == '__main__':
    
    
    # create message:
    ids_n0 = ["NCBIGene:100288687"]
    ids_n2 = ["MONDO:0008030"]
    predicates = ["biolink:interacts_with"]
    categories = ["biolink:ChemicalEntity","biolink:Gene"]


    json_pathfinder_message = TranslatorMessages.pathfinder_message(ids_n0, ids_n2, categories, predicates)

    
    aras_responses = TranslatorExtract.aras_submit(json_pathfinder_message,'dev')
    
    KG_flat = TranslatorExtract.get_KG_from_aras_message(aras_responses)
    
    app = cytoscape_layout_setup(KG_flat)
        
    Timer(1, open_browser).start()  
    
    
    app.run_server(debug=True, use_reloader=False)
    
    print('bob')