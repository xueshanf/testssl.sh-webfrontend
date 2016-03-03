#!/usr/bin/python3

from flask import Flask, request, redirect, session, render_template, url_for, flash
from os import urandom
from subprocess import check_output, Popen, PIPE, CalledProcessError, TimeoutExpired
from io import BytesIO
import re

app = Flask(__name__)

### Configuration ###
checkCmd = "testssl.sh/testssl.sh"
checkArgs = ["--quiet"]
checkTimeout = 90
rendererCmd = "aha"
rendererArgs = ["-n"]
rendererTimeout = 10
protocols = ["ftp", "smtp", "pop3", "imap", "xmpp", "telnet", "ldap"]
reHost = re.compile("^[a-z0-9]+(\.[a-z0-9]+)*$")
app.debug = False
app.secret_key = urandom(32)
#####################

@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'GET':                         # Main Page
        return render_template("main.html")
    elif request.method == 'POST':                      # Perform Test
        # Sanity checks of request values
        ok = True
        host = request.form['host']
        if not reHost.match(host):
            flash("Wrong host name!")
            ok = False

        try:
            port = int(request.form['port'])
            if not (port >= 0 and port <= 65535):
                flash("Wrong port number!")
                ok = False
        except:
            flash("Port number must be numeric")
            ok = False

        if 'starttls' in request.form and request.form['starttls'] == "yes":
            starttls = True
        else:
            starttls = False

        protocol = request.form['protocol']
        if starttls and protocol not in protocols:
            flash("Wrong protocol!")
            ok = False

        if not ok:
            return redirect(url_for('main'))

        # Build command line
        args = [checkCmd]
        args += checkArgs
        if starttls:
            args.append("-t")
            args.append(protocol)
        args.append(host + ":" + str(port))

        # Perform test
        output = b""
        try:
            check = Popen(args, stdout=PIPE, stderr=PIPE)
            output, err = check.communicate(timeout=checkTimeout)
            if check.returncode != 0:
                output = err
                flash("SSL Scan failed with error code " + str(check.returncode) + " - see below for details")
        except TimeoutExpired as e:
            flash("SSL Scan timed out")
            check.terminate()

        html = "<pre>" + str(output, 'utf-8') + "</pre>"
        try:
            renderer = Popen([rendererCmd], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            html, err = renderer.communicate(input=output, timeout=rendererTimeout)
            if renderer.returncode != 0:
                html = "<pre>" + str(err, 'utf-8') + "</pre>"
                flash("HTML formatting failed with error code " + str(renderer.returncode) + " - see raw output below")
        except TimeoutExpired as e:
            flash("HTML formatting failed - see raw output below")
            renderer.terminate()

        return render_template("result.html", result=str(html, 'utf-8'))

if __name__ == "__main__":
    app.run()
