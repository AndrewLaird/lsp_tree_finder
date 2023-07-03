import pylspclient
import os
import subprocess
import threading



class ReadPipe(threading.Thread):
    def __init__(self, pipe):
        threading.Thread.__init__(self)
        self.pipe = pipe

    def run(self):
        line = self.pipe.readline().decode('utf-8')
        while line:
            #print(line)
            line = self.pipe.readline().decode('utf-8')


def get_lsp_client():
    intelephense_cmd = ["intelephense", "--stdio"]
    p = subprocess.Popen(intelephense_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    json_rpc_endpoint = pylspclient.JsonRpcEndpoint(p.stdin, p.stdout)
    lsp_endpoint = pylspclient.LspEndpoint(json_rpc_endpoint)

    lsp_client = pylspclient.LspClient(lsp_endpoint)
    capabilities = {
        # Add your desired capabilities here
    }
    root_uri = os.path.abspath('./')  # Use a valid root URI for your PHP project
    workspace_folders = [{'name': 'php-lsp', 'uri': root_uri}]
    lsp_client.initialize(p.pid, None, root_uri, None, capabilities, "off", workspace_folders)
    lsp_client.initialized()
    return lsp_client, p


class PHP_LSP_CLIENT():
    def __init__(self):
        self.lsp_client, self.subprocess = get_lsp_client()
        pass

    """
    Row, col are zero index'ed (1 less than your editor)
    """
    def get_definitions(self, file_path, row, col):
        file_uri = "file://"+file_path

        results = None
        with open(file_path, "r") as text:
            languageId = pylspclient.lsp_structs.LANGUAGE_IDENTIFIER.PHP
            self.lsp_client.didOpen(pylspclient.lsp_structs.TextDocumentItem(file_uri, languageId, 1, text.read()))
            results = self.lsp_client.definition(pylspclient.lsp_structs.TextDocumentIdentifier(file_uri), pylspclient.lsp_structs.Position(row, col))
        return results
    
    def close(self):
        self.lsp_client.shutdown()
        self.lsp_client.exit()
        self.subprocess.kill()
