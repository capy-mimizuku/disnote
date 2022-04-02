import os
import sys
import common
import csv
import json
import pathlib
import shutil
from distutils import dir_util
from dateutil.parser import parse
from dateutil.parser import ParserError
from dateutil.relativedelta import relativedelta
import datetime
import codecs
import hashlib

logger = common.getLogger(__file__)

CONFIG_WORK_KEY = 'merge'

def main(input_files):

	logger.info("4. 結果マージ開始")

	personalData = {} # 話者情報

	# 出力するファイル名の決定
	basefilename = ""

	# 入力ファイルのハッシュ値を読み込む
	input_files.sort() # 入力ファイル名をソート（引数の順番だけ違う場合にファイル名を揃えるため）
	join_hash = "";
	for input_file in input_files:
		config = common.readConfig(input_file)
		hash = config['DEFAULT'].get("hash")
		join_hash += hash + "_"
		
		key = common.getFileNameWithoutExtension(input_file)
		personalData[key] = {"orgfile":os.path.basename(input_file), "hash": hash, "name": key}

	if len(input_files) <= 1: # ファイルが1つの場合はそのままのファイル名を使う
		basefilename = common.getFileNameWithoutExtension(input_files[0]) + "_disnote"
	else:
		basefilename = hashlib.md5(join_hash.encode()).hexdigest()[:8] + "_disnote" # ハッシュ値の先頭8文字だけ採用（まあ被らないでしょう…）

	l = list()

	# 認識結果ファイル(csv)を読み込んでマージする
	for input_file in input_files:
		recognize_result_file = common.getRecognizeResultFile(input_file)
		logger.info("認識結果ファイル：{}".format(recognize_result_file))

		with open(recognize_result_file , "r") as f:
			rows = csv.reader(f)
			l.extend(rows)

	l.sort(key = lambda x:int(x[2])) # 3列目（発話タイミング）でソート

	# ファイルパスを相対パスにする
	basedir = os.path.dirname(input_files[0]) # 入力音声ファイルの置いてあるディレクトリ
	for line in l:
		p = pathlib.Path(line[1]);
		line[1] = str(p.relative_to(basedir))

	# csvファイル出力
	merged_csv_file = os.path.join(basedir, basefilename + ".csv")
	logger.info("最終結果ファイル(csv)：{}".format(merged_csv_file))

	with open(merged_csv_file , "w", newline='' ) as f: # 変な改行が入るのを防ぐため newline='' 
		writer = csv.writer(f, quoting=csv.QUOTE_ALL)
		writer.writerow(["話者","ファイル","時間（ミリ秒）","長さ(ミリ秒)","スコア","候補1","候補2","候補3","候補4","候補5"]); # ヘッダ
		writer.writerows(l);

	# json(形式のjsファイル)
	#merged_js_file = common.getMergedJsFile(input_files[0])
	#logger.info("最終結果ファイル(json)：{}".format(merged_js_file))


	# Craigのinfo.txtを探す
	baseDate = None 
	try:
		infoFile = os.path.join(basedir, "info.txt")
		with open(infoFile , "r",  encoding="utf-8") as f:
			for line in f:
				segment = line.split("\t")
				if (len(segment) > 1 and segment[0] == "Start time:"): # 開始時刻があれば読む
					baseDate = parse(segment[1])
					break
	except ParserError:
		logger.info("info.txtのStart time: parse失敗")
	except FileNotFoundError:
		logger.info("info.txtなし")
	except :
		logger.info("info.txtの読み込み失敗")
	
	# index.htmlのオリジナル読み込み
	with open("src/index.html" , "r" ) as f:
		index_data = f.read()

	# JavaScriptの変数部分を作成
	merged_js = "results ="
	merged_js += json.dumps(l, indent=4, ensure_ascii=False)
	merged_js += ";\n";
	if(baseDate):
		baseDate += relativedelta(hours=+9)
		merged_js += "baseDate="
		merged_js += "new Date({},{},{},{},{},{})".format(baseDate.year, baseDate.month, baseDate.day, baseDate.hour, baseDate.minute, baseDate.second)
		merged_js += ";\n";
	merged_js += "personalData ="
	merged_js += json.dumps(personalData, indent=4, ensure_ascii=False)
	merged_js += ";\n";

	# index.html の値の部分を置換
	index_data = index_data.replace('RESULTS', merged_js)
	
	# index.html書き込み
	with open(os.path.join(basedir, basefilename + ".html") , "w", newline='' ) as f: # 変な改行が入るのを防ぐため newline='' 
		f.write(index_data)

	# htmlファイルなどをコピー
	# shutil.copyfile("src/index.html", os.path.join(basedir, "index.html"))
	dir_util.copy_tree("src/htmlfiles", os.path.join(basedir, "htmlfiles"))

	# プレイリスト作成(ファイルパスだけ書く)
	with codecs.open(os.path.join(basedir, basefilename + ".m3u8") , "w", "utf8", 'ignore') as f:
		for line in l:
			f.write(line[1])
			f.write("\n")

	logger.info(basefilename + ".htmlを出力しました。")
	logger.info("すべての処理が完了しました！")


# 直接起動した場合
if __name__ == "__main__":
	if len(sys.argv) < 2:
		logger.error("ファイルが指定されていません")
		sys.exit(1)

	index = 1
	l = list()
	while index < len(sys.argv):
		l.append(sys.argv[index])
		index += 1
	
	main(l)
