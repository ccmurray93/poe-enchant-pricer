import requests
import logging as log
import urllib
import re
from enchants.boots import *
from items.boots import *
import csv
import os
import time

log_format = "[%(asctime)s] [%(levelname)-5s] %(message)s"
log.basicConfig(format=log_format, level=log.INFO)



CHAOS_TO_EXALT = 110




def log_entry_exit(f):

    def wrapper(*f_args, **f_kwargs):
        log.debug("Entering - %s\n\targs: %s\n\tkwargs: %s" % (f.__name__, f_args, f_kwargs))
        ret = f(*f_args, **f_kwargs)
        log.debug("Exiting - %s\n\tReturn: %s" % (f.__name__, ret))
        return ret
    return wrapper

@log_entry_exit
def poe_trade_post(item_name, mod_groups, online=True):
    url = "http://poe.trade/search"

    mod_payload_serialized = ""
    mod_payload_list = []
    group_count = 0

    for group in mod_groups:
        group_count += 1
        mod_payload = {
            "mod_name": group["mod_name"],
            "mod_min": group.get("mod_min", ""),
            "mod_max": group.get("mod_max", ""),
            "mod_weight": "",
        }
        mod_payload_list.append(urllib.parse.urlencode(mod_payload))

    mod_payload_serialized = "&".join(mod_payload_list)

    group_payload = {
        "group_type": "And",
        "group_min": "",
        "group_max": "",
        "group_count": group_count,
    }

    mod_payload_serialized = mod_payload_serialized + "&" + urllib.parse.urlencode(group_payload)

    payload = {
        "league": "Bestiary",
        "name": item_name,
        "online": "x" if online else "",
        "has_buyout": 1,
        "corrupted": 0,
    }

    payload_serialized = urllib.parse.urlencode(payload)
    payload_serialized = payload_serialized + "&" + mod_payload_serialized

    log.debug("Payload: %s" % payload_serialized)

    response = requests.post(url, data=payload_serialized)
    return response.text

def parse_poe_trade_response(response):
    return re.findall(r"data-buyout=\"(.*?)\"", response)

@log_entry_exit
def query_poe_trade(item_name, mod_groups, limit=5):

    response = poe_trade_post(item_name, mod_groups, online=True)
    groups = parse_poe_trade_response(response)

    if len(groups) < 1:
        response = poe_trade_post(item_name, mod_groups, online=False)
        groups = parse_poe_trade_response(response)

    prices = []

    for price in groups:
        split = price.split(" ")
        price_amount = float(split[0])
        price_type = split[1]

        if (price_type == "chaos"):
            prices.append(price_amount)
        elif (price_type == "exalted"):
            prices.append(price_amount*CHAOS_TO_EXALT)

    if len(prices) > 0:
        prices.sort()

        count = limit
        if len(prices) < limit:
            count = len(prices)

        agg = {
            "min": prices[0],
            "avg": round(sum(prices[:limit])/count, 1),
            "count": count
        }
        return agg
    else:
        return None


if __name__ == "__main__":
    log.debug("Starting")

    items = [
        Goldwyrm,
        KaomsRoots,
        BonesOfUllr,
        DeathsDoor,
        AtzirisStep,
    ]

    enchants = [
        EnchantmentLifeAndManaRegenerationWhenHit3_,
        EnchantmentAddedFireDamageOnKill3,
        EnchantmentAddedChaosDamageWhenCrit3,
        EnchantmentAttackAndCastSpeedOnKill3,
        EnchantmentChanceCauseStatusAilmentsWhileHaventCrit3,
        EnchantmentColdDamageWhenHit3,
        EnchantmentCriticalChanceWhenNoCrit3,
        EnchantmentDodgeChanceWhenCrit3,
        EnchantmentElementalPenetrationWhileHaventKilled3,
        EnchantmentLifeAndManaLeechOnKill3,
        EnchantmentLightningDamageWhileHaventKilled3_,
        EnchantmentManaCostsWhenHit3,
        EnchantmentMovementVelocityWhileHaventBeenHit3,
        EnchantmentSpellDodgeWhenHitBySpells3,
        EnchantmentStunAvoidanceOnKill3,
    ]

    enchant_prices = []

    for item in items:
        # Get baseline price for non-corrupted item
        item_mod_group = item.search_terms
        item_prices = query_poe_trade(item_name=item.name, mod_groups=item_mod_group)
        item_avg_price = item_prices["avg"]
        log.info("%s - Base item price - %s" % (item.name, item_avg_price))
        for enchant in enchants:
            enchant_mod_groups = enchant.search_terms
            combined_mod_groups = enchant_mod_groups + item_mod_group
            prices = query_poe_trade(item_name=item.name, mod_groups=combined_mod_groups)
            log.info("%s - %s - %s" % (item.name, enchant.name, prices))
            enchant_price = {
                "item_name": item.name,
                "enchant_name": enchant.name,
                "enchant_profit": None
            }

            try:
                enchant_profit = round(prices["min"] - item_avg_price, 0)
            except:
                enchant_profit = "Not found"

            enchant_price["enchant_profit"] = enchant_profit
            enchant_prices.append(enchant_price)


    output_dir = os.path.join(os.path.dirname(__file__), "output")
    output_file_name = "enchant-profits-%s.csv" % round(time.time(), 0)
    output_file = os.path.join(output_dir, output_file_name)

    log.debug(enchant_prices)

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, sorted(enchant_prices[0].keys(), reverse=True))
        writer.writeheader()
        writer.writerows(enchant_prices)

    log.debug("Finished")