import subprocess
import pylspclient
import json
import time
import os

class LspClient:
    def __init__(self, host, port, process):
        self.process = process
        self.lsp_transport = pylspclient.LspEndpointTransport.connect_tcp(host, port)
        self.lsp_client = pylspclient.LspClient(self.lsp_transport)

        # Initialize the connection
        init_params = pylspclient.InitializeParams(processId=process.pid, rootUri=None,
                                                   capabilities={}, workspaceFolders=None)
        self.lsp_client.call('initialize', init_params)
        self.lsp_client.notify('initialized')

    def get_go_to_definition_response(self, line, character, filepath):
        # Perform the "go to definition" operation
        params = pylspclient.TextDocumentPositionParams(
            textDocument=pylspclient.TextDocumentIdentifier(uri=filepath),
            position=pylspclient.Position(line=line, character=character))
        response = self.lsp_client.call('textDocument/definition', params)

        # Parse the response
        response_data = json.loads(response)
        return response_data

    def close(self):
        # Close the connection
        self.lsp_client.call('shutdown', None)
        self.lsp_client.notify('exit', None)
        self.lsp_transport.close()

        # Terminate the language server process
        self.process.terminate()

    @staticmethod
    def create():
        intelephense_cmd = ["intelephense", "--stdio"]
        p = subprocess.Popen(intelephense_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give the server time to start
        return LspClient('localhost', 2089, p)

lsp_client = LspClient.create();
