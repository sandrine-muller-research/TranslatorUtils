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
            html.Tr([html.Td("Label"), html.Td(node_data['label'])]),
            html.Tr([html.Td("Info 1"), html.Td(node_data['info1'])]),
            html.Tr([html.Td("Info 2"), html.Td(node_data['info2'])]),
            html.Tr([html.Td("Info 3"), html.Td(node_data['info3'])])
        ])
    elif edge_data:
        return html.Table([
            html.Tr([html.Th("Edge Info")]),
            html.Tr([html.Td("Label"), html.Td(edge_data['label'])]),
            html.Tr([html.Td("Info 1"), html.Td(edge_data['info1'])]),
            html.Tr([html.Td("Info 2"), html.Td(edge_data['info2'])]),
            html.Tr([html.Td("Info 3"), html.Td(edge_data['info3'])])
        ])
    return "Click on a node or edge to see additional information"

def update_output_div(input_value):
    return f'Output: {input_value}'

def open_browser():
    webbrowser.open_new("http://localhost:8050")


def cytoscape_layout_setup(elements):
    # USAGE:
    #     elements = [
    #     {'data': {'id': 'one', 'label': 'Node 1'}},
    #     {'data': {'id': 'two', 'label': 'Node 2'}},
    #     {'data': {'source': 'one', 'target': 'two'}}
    # ]
    #  app = cytoscape_layout_setup(elements)
    
    app = Dash(__name__)

    app.layout = html.Div([
        cyto.Cytoscape(
            id='Translator-cytoscape-fullscreen',
            layout={'name': 'cose'},
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
    ids_n0 = ["CHEBI:31690"]
    ids_n2 = ["MONDO:0004784"]
    predicates = ["biolink:related_to"]


    json_pathfinder_message = TranslatorMessages.pathfinder_message(ids_n0, ids_n2, predicates)

    
    aras_responses = TranslatorExtract.aras_submit(json_pathfinder_message,'dev')
    
    KG_flat = TranslatorExtract.get_KG_from_aras_message(aras_responses)
    
    
        
    Timer(1, open_browser).start()  
    app = cytoscape_layout_setup(KG_flat)
    
    app.run_server(debug=True, port=8050, use_reloader=False, callback=open_browser)
    
    print('bob')