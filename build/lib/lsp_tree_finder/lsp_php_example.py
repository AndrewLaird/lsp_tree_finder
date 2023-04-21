import contextlib
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


@contextlib.contextmanager
def get_lsp_client():
    intelephense_cmd = ["intelephense", "--stdio"]
    p = subprocess.Popen(intelephense_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    read_pipe = ReadPipe(p.stderr)
    read_pipe.start()
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
    try:
        yield lsp_client
    finally:
        lsp_client.shutdown()
        lsp_client.exit()



# try:
    # symbols = lsp_client.documentSymbol(pylspclient.lsp_structs.TextDocumentIdentifier(uri))
    # for symbol in symbols:
        # print(symbol.name)
# except Exception as e: 
    # # documentSymbol is supported from version 8.
    # print("Failed to document symbols", e)

class Position(object):
    def __init__(self, line, character):
        """
        Constructs a new Position instance.

        :param int line: Line position in a document (zero-based).
        :param int character: Character offset on a line in a document (zero-based).
        """
        self.line = line
        self.character = character


class Range(object):
    def __init__(self, start, end):
        """
        Constructs a new Range instance.

        :param Position start: The range's start position.
        :param Position end: The range's end position.
        """
        self.start = to_type(start, Position)
        self.end = to_type(end, Position)





if __name__ == "__main__":
    with get_lsp_client() as lsp_client:

        file_path = os.path.abspath("./test1.php")
        uri = "file://" + file_path
        print(uri, file_path)

        text = open(file_path, "r").read()
        languageId = pylspclient.lsp_structs.LANGUAGE_IDENTIFIER.PHP
        version = 1
        lsp_client.didOpen(pylspclient.lsp_structs.TextDocumentItem(uri, languageId, version, text))

        print('----------------------------')
        result = lsp_client.definition(pylspclient.lsp_structs.TextDocumentIdentifier(uri), pylspclient.lsp_structs.Position(5, 21))
        print("result-----", result[0])
        print(result[0].__dict__)
        location: Position = result[0].uri
        range: Range = result[0].range
        print("~~~~~~~~~")
        print(location, range, range)

