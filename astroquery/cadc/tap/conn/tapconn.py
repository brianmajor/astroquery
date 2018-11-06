# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
=============
TAP plus
=============

"""
from astroquery.cadc.tap.xmlparser import utils
from astroquery.cadc.tap import taputils

try:
    # python 3
    import http.client as httplib
except ImportError:
    # python 2
    import httplib

from base64 import b64encode
import ssl
from astropy.extern.six.moves.urllib.parse import urlencode

import mimetypes
import time

__all__ = ['TapConn']

CONTENT_TYPE_POST_DEFAULT = "application/x-www-form-urlencoded"


class TapConn(object):
    """TAP plus connection class
    Provides low level HTTP connection capabilities
    """
    def __init__(self, ishttps, host, server_context, tap_context=None,
                 port=80, sslport=443, connhandler=None):
        """Constructor

        Parameters
        ----------
        ishttps: bool, mandatory
            'True' is the protocol to use is HTTPS
        host : str, mandatory
            host name
        server_context : str, mandatory
            server context
        tap_context : str, optional
            tap context
        port : int, optional, default 80
            HTTP port
        sslport : int, optional, default 443
            HTTPS port
        connhandler connection handler object, optional, default None
            HTTP(s) connection hander (creator). If no handler is provided, a
            new one is created.
        """
        self.__interna_init()
        self.__isHttps = ishttps
        self.__connHost = host
        self.__connPort = port
        self.__connPortSsl = sslport
        if server_context is not None:
            if(server_context.startswith("/")):
                self.__serverContext = server_context
            else:
                self.__serverContext = "/" + server_context
        else:
            self.__serverContext = ""
        if (tap_context is not None and tap_context != ""):
            if(tap_context.startswith("/")):
                self.__tapContext = self.__serverContext + tap_context
            else:
                self.__tapContext = self.__serverContext + "/" + tap_context
        else:
            self.__tapContext = self.__serverContext
        if connhandler is None:
            self.__connectionHandler = ConnectionHandler(self.__connHost,
                                                         self.__connPort,
                                                         self.__connPortSsl)
        else:
            self.__connectionHandler = connhandler

    def __interna_init(self):
        self.__connectionHandler = None
        self.__isHttps = False
        self.__connHost = ""
        self.__connPort = 80
        self.__connPortSsl = 443
        self.__serverContext = None
        self.__tapContext = None
        self.__postHeaders = {
            "Content-type": CONTENT_TYPE_POST_DEFAULT,
            "Accept": "text/plain"
        }
        self.__getHeaders = {}
        self.__cookie = None
        self.__currentStatus = 0
        self.__currentReason = ""

    def __get_tap_context(self, listName):
        return self.__tapContext + "/" + listName

    def execute_get(self, subcontext, verbose=False,
                    otherlocation=None, authentication=None):
        """Executes a GET request
        The connection is done through HTTP

        Parameters
        ----------
        subcontext : str, mandatory
            context to be added to host+serverContext+tapContext, usually the
            TAP list name
        verbose : bool, optional, default 'False'
            flag to display information about the process
        otherlocation: str, optional
            when redirecting the url might not be in the same context as the
            TAP service so otherlocation is a full url to use
            in the GET request
        authentication : AuthMethod object, mandatory, default 'None'
            authentication object to use

        Returns
        -------
        An HTTP response object
        """
        conn = self.__get_connection(verbose)
        if otherlocation is None:
            context = self.__get_tap_context(subcontext)
        else:
            context = otherlocation

        if authentication.get_auth_method() == 'netrc':
            user = authentication.get_auth(self.__connHost)
            cred = bytes(user[0] + ":" + user[1], encoding='ascii')
            userAndPass = b64encode(cred).decode("ascii")
            headers = {'Authorization': 'Basic %s' % userAndPass}
            authHeaders = dict(self.__getHeaders)
            authHeaders.update(headers)
        else:
            authHeaders = self.__getHeaders

        conn.request("GET", context, None, authHeaders)
        response = conn.getresponse()
        self.__currentReason = response.reason
        self.__currentStatus = response.status
        return response

    def execute_get_secure(self, subcontext, verbose=False,
                           otherlocation=None, authentication=None):
        """Executes a GET request
        The connection is done through HTTPS

        Parameters
        ----------
        subcontext : str, mandatory
            context to be added to host+serverContext+tapContext, usually the
            TAP list name
        verbose : bool, optional, default 'False'
            flag to display information about the process
        otherlocation: str, optional
            when redirecting the url might not be in the same context as the
            TAP service so otherlocation is a full url to use in
            the GET request
        authentication : AuthMethod object, mandatory, default 'None'
            authentication object to use

        Returns
        -------
        An HTTPS response object
        """
        conn = self.__get_connection_secure(
            verbose,
            certificate=authentication.get_certificate())
        if otherlocation is None:
            context = self.__get_tap_context(subcontext)
        else:
            context = otherlocation
        conn.request("GET", context, None, self.__getHeaders)
        response = conn.getresponse()
        self.__currentReason = response.reason
        self.__currentStatus = response.status
        return response

    def execute_post(self, subcontext, data,
                     content_type=CONTENT_TYPE_POST_DEFAULT,
                     verbose=False, authentication=None):
        """Executes a POST request
        The connection is done through HTTP

        Parameters
        ----------
        subcontext : str, mandatory
            context to be added to host+serverContext+tapContext, usually the
            TAP list name
        data : str, mandatory
            POST data
        content_type:str, optional, default 'application/x-www-form-urlencoded'
            HTTP(s) content-type header value
        verbose : bool, optional, default 'False'
            flag to display information about the process
        authentication : AuthMethod object, mandatory, default 'None'
            authentication object to use

        Returns
        -------
        An HTTP(s) response object
        """
        conn = self.__get_connection(verbose)
        self.__postHeaders["Content-type"] = content_type
        if authentication.get_auth_method() == 'netrc':
            user = authentication.get_auth(self.__connHost)
            cred = bytes(user[0] + ":" + user[1], encoding='ascii')
            userAndPass = b64encode(cred).decode("ascii")
            headers = {'Authorization': 'Basic %s' % userAndPass}
            authHeaders = dict(self.__postHeaders)
            authHeaders.update(headers)
        else:
            authHeaders = self.__postHeaders

        context = self.__get_tap_context(subcontext)
        conn.request("POST", context, data, authHeaders)
        response = conn.getresponse()
        self.__currentReason = response.reason
        self.__currentStatus = response.status
        return response

    def execute_post_secure(self, subcontext, data,
                            content_type=CONTENT_TYPE_POST_DEFAULT,
                            verbose=False, authentication=None):
        """Executes a POST request
        The connection is done through HTTPS

        Parameters
        ----------
        subcontext : str, mandatory
            context to be added to host+serverContext+tapContext, usually the
            TAP list name
        data : str, mandatory
            POST data
        content_type:str, optional, default 'application/x-www-form-urlencoded'
            HTTP(s) content-type header value
        verbose : bool, optional, default 'False'
            flag to display information about the process
        authentication : AuthMethod object, mandatory, default 'None'
            authentication object to use

        Returns
        -------
        An HTTPS response object
        """
        conn = self.__get_connection_secure(
            verbose,
            certificate=authentication.get_certificate())
        self.__postHeaders["Content-type"] = content_type
        context = self.__get_tap_context(subcontext)
        conn.request("POST", context, data, self.__postHeaders)
        response = conn.getresponse()
        self.__currentReason = response.reason
        self.__currentStatus = response.status
        return response

    def get_response_status(self):
        """Returns the latest connection status

        Returns
        -------
        The current (latest) HTTP(s) response status
        """
        return self.__currentStatus

    def get_response_reason(self):
        """Returns the latest connection reason (message)

        Returns
        -------
        The current (latest) HTTP(s) response reason
        """
        return self.__currentReason

    def url_encode(self, data):
        """Encodes the provided dictionary

        Parameters
        ----------
        data : dictionary, mandatory
            dictionary to be encoded
        """
        return urlencode(data)

    def find_header(self, headers, key):
        """Searches for the specified keyword

        Parameters
        ----------
        headers : HTTP(s) headers object, mandatory
            HTTP(s) response headers
        key : str, mandatory
            header key to be searched for

        Returns
        -------
        The requested header value or None if the header is not found
        """
        return taputils.taputil_find_header(headers, key)

    def save_to_file(self, output, response):
        """Writes the connection response into the specified output

        Parameters
        ----------
        output : file, mandatory
            output file
        response : HTTP(s) response object, mandatory
            HTTP(s) response object
        """
        with open(output, "wb") as f:
            while True:
                data = response.read(4096)
                if len(data) < 1:
                    break
                f.write(data)
            f.close()

    def get_suitable_extension_by_format(self, output_format):
        """Returns the suitable extension for a file based on the output format

        Parameters
        ----------
        output_format : output format, mandatory

        Returns
        -------
        The suitable file extension based on the output format
        """
        if output_format is None:
            return ".vot"
        ext = ""
        outputFormat = output_format.lower()
        if "vot" in outputFormat:
            ext += ".vot"
        elif "xml" in outputFormat:
            ext += ".xml"
        elif "json" in outputFormat:
            ext += ".json"
        elif "plain" in outputFormat:
            ext += ".txt"
        elif "csv" in outputFormat:
            ext += ".csv"
        elif "ascii" in outputFormat:
            ext += ".ascii"
        return ext

    def get_suitable_extension(self, headers):
        """Returns the suitable extension for a file based on the headers
        received

        Parameters
        ----------
        headers : HTTP(s) response headers object, mandatory
            HTTP(s) response headers

        Returns
        -------
        The suitable file extension based on the HTTP(s) headers
        """
        if headers is None:
            return ""
        ext = ""
        contentType = self.find_header(headers, 'Content-Type')
        if contentType is not None:
            contentType = contentType.lower()
            if "xml" in contentType:
                ext += ".xml"
            elif "json" in contentType:
                ext += ".json"
            elif "plain" in contentType:
                ext += ".txt"
            elif "csv" in contentType:
                ext += ".csv"
            elif "ascii" in contentType:
                ext += ".ascii"
        contentEncoding = self.find_header(headers, 'Content-Encoding')
        if contentEncoding is not None:
            if "gzip" == contentEncoding.lower():
                ext += ".gz"
        return ext

    def get_host_url(self):
        """Returns the host+port+serverContext

        Returns
        -------
        A string composed of: 'host:port/server_context'
        """
        return str(self.__connHost) + ":" + str(self.__connPort) \
            + str(self.__get_tap_context(""))

    def get_host_url_secure(self):
        """Returns the host+portSsl+serverContext

        Returns
        -------
        A string composed of: 'host:portSsl/server_context'
        """
        return str(self.__connHost) + ":" + str(self.__connPortSsl) \
            + str(self.__get_tap_context(""))

    def check_launch_response_status(self, response, debug,
                                     expected_response_status):
        """Checks the response status code
        Return True if the response status code is the expected_response_status

        Parameters
        ----------
        response : HTTP(s) response object, mandatory
            HTTP(s) response
        debug : bool, mandatory
            flag to display information about the process
        expected_response_status : int, mandatory
            expected response status code

        Returns
        -------
        'True' if the HTTP(s) response status is the provided
        'expected_response_status' argument
        """
        isError = False
        if response.status != expected_response_status:
            if debug:
                print("ERROR: " + str(response.status) + ": " +
                      str(response.reason))
            isError = True
        return isError

    def __get_connection(self, verbose=False):
        return self.__connectionHandler.get_connection(self.__isHttps, verbose)

    def __get_connection_secure(self, verbose=False, certificate=None):
        return self.__connectionHandler.get_connection_secure(
            verbose,
            certificate=certificate)

    def encode_multipart(self, fields, files):
        """Encodes a multipart form request

        Parameters
        ----------
        fields : dictionary, mandatory
            dictionary with keywords and values
        files : array with key, filename and value, mandatory
            array with key, filename, value

        Returns
        -------
        The suitable content-type and the body for the request
        """
        timeMillis = int(round(time.time() * 1000))
        boundary = '***%s***' % str(timeMillis)
        CRLF = '\r\n'
        multiparItems = []
        for key in fields:
            multiparItems.append('--' + boundary + CRLF)
            multiparItems.append(
                'Content-Disposition: form-data; name="%s"%s' % (key, CRLF))
            multiparItems.append(CRLF)
            multiparItems.append(fields[key]+CRLF)
        for (key, filename, value) in files:
            multiparItems.append('--' + boundary + CRLF)
            multiparItems.append(
                'Content-Disposition: form-data; name="%s"; filename="%s"%s' %
                (key, filename, CRLF))
            multiparItems.append(
                'Content-Type: %s%s' %
                (mimetypes.guess_extension(filename), CRLF))
            multiparItems.append(CRLF)
            multiparItems.append(value)
            multiparItems.append(CRLF)
        multiparItems.append('--' + boundary + '--' + CRLF)
        multiparItems.append(CRLF)
        body = utils.util_create_string_from_buffer(multiparItems)
        contentType = 'multipart/form-data; boundary=%s' % boundary
        return contentType, body

    def __str__(self):
        return "\tHost: " + str(self.__connHost) + "\n\tUse HTTPS: " \
            + str(self.__isHttps) \
            + "\n\tPort: " + str(self.__connPort) + "\n\tSSL Port: " \
            + str(self.__connPortSsl)


class ConnectionHandler(object):
    def __init__(self, host, port, sslport):
        self.__connHost = host
        self.__connPort = port
        self.__connPortSsl = sslport

    def get_connection(self, ishttps=False, verbose=False):
        if ishttps:
            if verbose:
                print("------>https")
            return self.get_connection_secure(verbose)
        else:
            if verbose:
                print("------>http")
            return httplib.HTTPConnection(self.__connHost, self.__connPort)

    def get_connection_secure(self, verbose, certificate=None):
        context = ssl.create_default_context()
        context.load_cert_chain(certificate)
        return httplib.HTTPSConnection(self.__connHost,
                                       self.__connPortSsl,
                                       context=context)
