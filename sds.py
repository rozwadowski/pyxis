#!/usr/bin/python
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('adm.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/paragonySDS', methods=['GET', 'POST'])
@app.route('/paragonySDS/', methods=['GET', 'POST'])
def paragonySDS():
    if request.method == 'POST':
        imap = request.form['imap']
        login = request.form['login']
        psw = request.form['password']
        sourceMail = request.form['login']
        folder = request.form['folder']
        device = request.form['device']
        date = request.form['data']

        raport = {"date": "0000-00-00", "error": "", "repCnt": 0, "cash_grs": 0, "cash_net": 0,
                  "cash_tax": [0, 0, 0, 0, 0], "cnt_cash": 0, "cash_netABCDE": [0, 0, 0, 0, 0],
                  "card_grs": 0, "card_net": 0, "card_tax": [0, 0, 0, 0, 0], "cnt_card": 0,
                  "card_netABCDE": [0, 0, 0, 0, 0], "charge_grs": 0, "charge_net": 0, "charge_tax": 0,
                  "cnt_charge": 0}
        if imap is not None:
            import parSDS
            raport = parSDS.raport(imap, login, psw, sourceMail, folder, device, date)

        return render_template('paragonySDS.html', printout=raport)
    else:
        raport = {"date": "0000-00-00", "error": "", "repCnt": 0, "cash_grs": 0, "cash_net": 0,
                  "cash_tax": [0, 0, 0, 0, 0],
                  "cnt_cash": 0, "cash_netABCDE": [0, 0, 0, 0, 0], "card_grs": 0, "card_net": 0,
                  "card_tax": [0, 0, 0, 0, 0], "cnt_card": 0, "card_netABCDE": [0, 0, 0, 0, 0],
                  "charge_grs": 0, "charge_net": 0, "charge_tax": 0, "cnt_charge": 0}
        return render_template('paragonySDS.html', printout=raport)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
