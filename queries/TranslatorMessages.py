

def pathfinder_message(ids_n0, ids_n2, predicates):
    message = {
        "message" : {
          "query_graph": {
              "nodes": {
                  "n0": {
                      "ids": ids_n0
                      },
                  "un": {
                      "categories": [
                          "biolink:NamedThing"
                          ]
                      },
                  "n2": {
                      "ids": ids_n2
                      }
                  },
              "edges": {
                  "e0": {
                      "subject": "n0",
                      "object": "un",
                      "predicates": predicates,
                      "knowledge_type": "inferred"
                      },
                  "e1": {
                      "subject": "un",
                      "object": "n2",
                      "predicates": predicates,
                      "knowledge_type": "inferred"
                      },
                  "e2": {
                      "subject": "n0",
                      "object": "n2",
                      "predicates": predicates,
                      "knowledge_type": "inferred"
                      }
                  }
              }
          }
        }
    
    return message
