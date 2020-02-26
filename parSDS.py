#!/usr/bin/python
# ParagonySDS - program do pobierania raportów dobowych i zliczania płatności kartą oraz gotówką
# Autor: Piotr Rozwadowski rozwadowski@sds.uw.edu.pl siotsonek@gmail.com

import imaplib
import re
import datetime


def pick_mails(date, results):
    mail_index = []
    for res in results:
        regex = "[0-9]{2}-[0-9]{2}-[0-9]{4}"
        if len(re.findall(regex, res)) > 0:
            all_dates = re.findall(regex, res)
            dates = list(set(all_dates))
            dates_cnt = [all_dates.count(i) for i in dates]
            max_dates = dates_cnt.index(max(dates_cnt))
            if date == dates[max_dates]:
                mail_index.append(results.index(res))
    return mail_index


def processing(mail_index, results, payment):
    grs, tax, cnt = 0., [0., 0., 0., 0., 0.], 0
    net = [0., 0., 0., 0., 0.]
    taxes = [0.23, 0.08, 0.05, 0.0, 0.0]
    for i in mail_index:
        lines = results[i].split("\n")
        ind = 0
        for line in lines:
            regex = payment + ":[ ]+([0-9.]+)"
            if len(re.findall(regex, line)) > 0:
                grs += float(re.findall(regex, line)[0])
                if len(re.findall('Reszta \(' + payment + ' PLN\):[ ]+([0-9.]+)', lines[ind + 1])) > 0:
                    grs -= float(re.findall('Reszta \(' + payment + ' PLN\):[ ]+([0-9.]+)', lines[ind + 1])[0])
                cnt += 1

                a = ind
                b = a
                while len(re.findall("RAZEM:", lines[a])) == 0:
                    a = a - 1
                # print(a,b)
                for k in range(a + 2, b):
                    for t in "ABCDE":
                        if len(re.findall("Sprzedaż opodatkowana " + t + ":[ ]+([0-9.]+)", lines[k])) > 0:
                            sp = float(re.findall("Sprzedaż opodatkowana " + t + ":[ ]+([0-9.]+)", lines[k])[0])
                            net["ABCDE".index(t)] += float(
                                re.findall("Sprzedaż opodatkowana " + t + ":[ ]+([0-9.]+)", lines[k])[0]) / (
                                                             1.0 + taxes["ABCDE".index(t)])
                            tax["ABCDE".index(t)] += sp - sp / (taxes["ABCDE".index(t)] + 1.0)
                        if len(re.findall("Sprzedaż zwolniona " + t + ":[ ]+([0-9.]+)", lines[k])) > 0:
                            sp = float(re.findall("Sprzedaż zwolniona " + t + ":[ ]+([0-9.]+)", lines[k])[0])
                            net["ABCDE".index(t)] += float(
                                re.findall("Sprzedaż zwolniona " + t + ":[ ]+([0-9.]+)", lines[k])[0]) / (
                                                             1.0 + taxes["ABCDE".index(t)])
            ind += 1

    return grs, round(grs - sum([round(t, 2) for t in tax]), 2), [round(t, 2) for t in tax], cnt, [round(t, 2) for t in
                                                                                                   net]


def summary(mail_index, results):
    grs, net, tax, cnt = 0., 0., 0., 0
    for i in mail_index:
        lines = results[i].split("\n")
        for line in lines:
            # Należność:                      PLN 112.00
            regex = "Należność:[ ]+PLN ([0-9.]+)"
            if len(re.findall(regex, line)) > 0:
                grs += float(re.findall(regex, line)[0])
                cnt += 1
                # SUMA PTU                             11.91
                regex = "SUMA PTU[ ]+([0-9.]+)"
                tax += float(re.findall(regex, lines[lines.index(line) - 2])[0])
            # Sprzedaż netto w stawce D             0.00
            regex = "Sprzedaż netto w stawce [ABCD]{1}[ ]+([0-9.]+)"
            if len(re.findall(regex, line)) > 0:
                net += float(re.findall(regex, line)[0])
            # Sprzedaż zwolniona E                  0.00
            regex = "Sprzedaż zwolniona E[ ]+([0-9.]+)"
            if len(re.findall(regex, line)) > 0:
                net += float(re.findall(regex, line)[0])
    return round(grs, 2), round(net, 2), round(tax, 2), cnt


def raport(imap_server: str, mail_login: str, mail_pass: str, mail_from: str, mail_folder: str,
           cash_name: str, dat: str) -> dict:
    # connect to server
    try:
        mail_date = [int(i) for i in dat.split("-")][::-1]
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(mail_login, mail_pass)
        mail.list()
        mail.select(mail_folder)
        # parse date
        date_since = (datetime.date(mail_date[2], mail_date[1], mail_date[0])
                      - datetime.timedelta(5)).strftime("%d-%b-%Y")
        date_before = (datetime.date(mail_date[2], mail_date[1], mail_date[0])
                       + datetime.timedelta(5)).strftime("%d-%b-%Y")
        # search email
        status, response = mail.search(None, '(FROM "' + mail_from + '")', 'SUBJECT "*[' + cash_name + ']*"',
                                       '(SINCE {date})'.format(date=date_since),
                                       '(BEFORE {date})'.format(date=date_before))

        messages_uid = re.findall("[0-9]+", str(response[0]))

        results = []
        for uid in messages_uid:
            _, res = mail.fetch(uid, '(UID BODY[TEXT])')
            results.append(res[0][1].decode("utf-8"))

        mail_index = pick_mails("-".join([str(i) for i in dat.split("-")][::-1]), results)

        cash_grs, cash_net, cash_tax, cnt_cash, cash_netABCDE = processing(mail_index, results, "Gotówka")
        card_grs, card_net, card_tax, cnt_card, card_netABCDE = processing(mail_index, results, "Karta")
        charge_grs, charge_net, charge_tax, cnt_charge = summary(mail_index, results)

        # validation
        errors = ""
        if abs(cash_grs + card_grs - charge_grs) > 10e-3:
            errors += "Niezgodne kwoty brutto <br>"
        if abs(cash_net + card_net - charge_net) > 10e-3:
            errors += "Niezgodne kwoty netto<br>"
        if abs(sum(cash_netABCDE) - cash_net) > 10e-3:
            errors += "Niezgodne kwoty netto według stawek A-E (gotówka)<br>"
        if abs(sum(card_netABCDE) - card_net) > 10e-3:
            errors += "Niezgodne kwoty netto według stawek A-E (karta)<br>"
        if abs(sum(cash_tax) + sum(card_tax) - charge_tax) > 10e-3:
            errors += "Niezgodna suma PTU<br>"
        if len(mail_index) > 1:
            errors += "Uwaga: pobrano więcej niż jeden raport dobowy<br>"
        if len(mail_index) != cnt_charge:
            errors += "Niezgodna liczba raportów<br>"

        printout = {"date": dat, "error": errors, "repCnt": len(mail_index), "cash_grs": cash_grs,
                    "cash_net": cash_net, "cash_tax": cash_tax, "cnt_cash": cnt_cash,
                    "cash_netABCDE": cash_netABCDE, "card_grs": card_grs, "card_net": card_net,
                    "card_tax": card_tax, "cnt_card": cnt_card, "card_netABCDE": card_netABCDE,
                    "charge_grs": charge_grs, "charge_net": charge_net, "charge_tax": charge_tax,
                    "cnt_charge": cnt_charge}
    except ValueError:
        return {"error": "Błędna data"}
    except imaplib.IMAP4.error:
        return {"error": "Brak loginu lub hasła"}

    return printout
