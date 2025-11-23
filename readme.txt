ps aux | grep python



# Docker 启动

```
docker build -t HiFate-bazi:latest .
docker run -d --name HiFate-bazi -p 8001:8001 --env-file .env HiFate-bazi:latest
# 或使用 docker compose up -d （参见 docs/docker_deployment.md）
```

# 本地启动  start

#计算基本八字信息


curl -X POST http://127.0.0.1:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'


# -- 生成界面展示信息（命宫、身宫等）

curl -X POST http://127.0.0.1:8001/api/v1/bazi/interface \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "name": "张三",
    "location": "北京"
  }'




# 计算详细八字（含大运流年序列）

curl -X POST http://127.0.0.1:8001/api/v1/bazi/detail \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'



#-- ai接口

  curl -X POST http://127.0.0.1:8001/api/v1/bazi/ai-analyze \
    -H "Content-Type: application/json" \
    -d '{
      "solar_date": "1990-05-15",
      "solar_time": "14:30",
      "gender": "male",
      "user_question": "请分析我的财运和事业"
    }'




#查看健康检查：
curl http://127.0.0.1:8001/health

#测试缓存：
#相同参数的请求第二次会更快（从缓存返回）

# 检查服务状态

brew services list | grep mysql


        self.connection_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),  # Docker用'mysql'，本地默认'localhost'
            'port': int(os.getenv('MYSQL_PORT', 3306)),    # Docker和本地默认都是3306（本地若改了端口需手动改）
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', '123456'),  # 本地MySQL密码若不同，这里直接改
            'database': os.getenv('MYSQL_DATABASE', 'testdb'),
            'charset': 'utf8mb4'
        }


#规则

curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "rule_types": ["rizhu_gender_dynamic"]
  }'



   curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
     -H 'Content-Type: application/json' \
     -d '{"solar_date":"1990-05-15","solar_time":"14:30","gender":"male","rule_types":["rizhu_gender_dynamic"]}'





curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{
        "solar_date": "1996-06-17",
        "solar_time": "14:30",
        "gender": "male",
        "rule_types": ["marriage_ten_gods", "rizhu_gender_dynamic"],
        "include_bazi": true
      }'



# 任务

调用 基于langchain  coze

规则引擎与数据库

充值 商城

? 男女一样   资料相差不大
? 什么年  什么月  需要转换
？增加互联网


# 明日计划  打通 ai 效果 ，串联起来 。
# 明日任务  解决调用ai  反应慢的问题




--  星宿  人员司令分野


阴阳  天干地支

面相 八卦 易经 奇门


存什么
微服务
商城体系  通信体系  缓存 消息  增提处理
api

数据边界  数据安全 流转   我们说了算
逻辑边界  数据 大模型算法
中间层  api 统一网管      如何和三方对接  我们包装  证书定期续签

审核  会员中心  点击按钮   商城  技术方案
封装接口 加密  参数   ，

相同的参数 一次生效 多次调用不生效

用户  后期收回

埋点

上线后都有收回


使用 od 联合开发的流程与方法论


面相 大运流年  根据后端计算出来追加上去  ，手相 办公室  一样的套路  
面相 手相 八字 办公室分水 整合的命理分析   命里缺木  需要在办公桌上面放个花

星座运势  有相应的插件  


模型月规则



{"success":true,"bazi_data":{"bazi":{"basic_info":{"solar_date":"1990-05-15","solar_time":"14:30","lunar_date":{"year":1990,"month":4,"day":21},"gender":"male"},"bazi_pillars":{"year":{"stem":"庚","branch":"午"},"month":{"stem":"辛","branch":"巳"},"day":{"stem":"庚","branch":"辰"},"hour":{"stem":"癸","branch":"未"}},"details":{"year":{"main_star":"比肩","hidden_stars":["正官","正印"],"hidden_stems":["丁火","己土"],"star_fortune":"沐浴","self_sitting":"沐浴","kongwang":"戌亥","nayin":"路旁土","deities":["月德贵人","德秀贵人","福星贵人"]},"month":{"main_star":"劫财","hidden_stars":["七杀","比肩","偏印"],"hidden_stems":["丙火","庚金","戊土"],"star_fortune":"长生","self_sitting":"死","kongwang":"申酉","nayin":"白蜡金","deities":["天德贵人","地网","德秀贵人","劫煞","亡神"]},"day":{"main_star":"元男","hidden_stars":["偏印","正财","伤官"],"hidden_stems":["戊土","乙木","癸水"],"star_fortune":"养","self_sitting":"养","kongwang":"申酉","nayin":"白蜡金","deities":["寡宿","月德贵人","童子煞","魁罡","十恶大败","德秀贵人","流霞","天医","国印贵人","吊客"]},"hour":{"main_star":"伤官","hidden_stars":["正印","正官","正财"],"hidden_stems":["己土","丁火","乙木"],"star_fortune":"冠带","self_sitting":"墓","kongwang":"申酉","nayin":"杨柳木","deities":["天乙贵人","童子煞"]}},"ten_gods_stats":{"main":{"比肩":{"count":1,"pillars":{"year":1}},"劫财":{"count":1,"pillars":{"month":1}},"元男":{"count":1,"pillars":{"day":1}},"伤官":{"count":1,"pillars":{"hour":1}}},"sub":{"正官":{"count":2,"pillars":{"year":1,"hour":1}},"正印":{"count":2,"pillars":{"year":1,"hour":1}},"七杀":{"count":1,"pillars":{"month":1}},"比肩":{"count":1,"pillars":{"month":1}},"偏印":{"count":2,"pillars":{"month":1,"day":1}},"正财":{"count":2,"pillars":{"day":1,"hour":1}},"伤官":{"count":1,"pillars":{"day":1}}},"totals":{"比肩":{"count":2,"pillars":{"year":1,"month":1}},"正官":{"count":2,"pillars":{"year":1,"hour":1}},"正印":{"count":2,"pillars":{"year":1,"hour":1}},"劫财":{"count":1,"pillars":{"month":1}},"七杀":{"count":1,"pillars":{"month":1}},"偏印":{"count":2,"pillars":{"month":1,"day":1}},"元男":{"count":1,"pillars":{"day":1}},"正财":{"count":2,"pillars":{"day":1,"hour":1}},"伤官":{"count":2,"pillars":{"day":1,"hour":1}}}}},"rizhu":"庚辰","matched_rules":[{"rule_code":"RZ_庚辰_male","rule_name":"庚辰男命分析","rule_type":"rizhu_gender","priority":100,"contents":[{"type":"description","text":"都有婚姻不理想的一面更有婚姻不顺的征兆。"},{"type":"description","text":"有秉权好杀的一面。"},{"type":"description","text":"以能从事武职（公检法军警宪或武术教练）为佳。"},{"type":"description","text":"虽然具有魁罡的刚强性格，做任何事情，都要求圆满，但是他们也有敬老怜下，没有自负的精神，对于任何事，都会首先考虑别人立场和利益的特点。"},{"type":"description","text":"才能优秀，在单位上，容易受到上级的赏识和提拔，因此容易成功。"},{"type":"description","text":"但是多有遍游异乡、旅行、经商的征兆。"},{"type":"description","text":"在夫妻关系中，都是对方对自己实质性的爱，超过了自己对对方实质的性爱。"},{"type":"description","text":"和属鼠、属猴的人很合得来，大家在一起的心情很舒畅。"},{"type":"description","text":"能够激发自己的聪明才智，但也能促使自己目中无人。"},{"type":"description","text":"所以要警惕。"},{"type":"description","text":"和属虎、属兔的人也能交上朋友。"},{"type":"description","text":"属虎、属兔的人往往会给自己带来财运或者有关发财的信息。"},{"type":"description","text":"和属鸡的人也很合得来。"},{"type":"description","text":"但要注意，若自己正在恋爱中，和属鸡的人在一起，自己的恋爱，或者婚姻，则容易出现问题。"},{"type":"description","text":"若逢狗的大运、流年，则容易有乔迁之事发生，甚至出现职地之变。"},{"type":"description","text":"是太阳经被引动，容易引发生理上诸如头痛、胃病、小便清冷、消渴、胸胁腹痛、左臂、右腿寒病等症。"}]}]},"matched_rules":[{"rule_id":"DYNAMIC_RIZHU_GENDER","rule_code":"DYNAMIC_RIZHU_GENDER","rule_name":"日柱性别动态查询","rule_type":"rizhu_gender_dynamic","priority":100,"content":{"type":"description","items":[{"type":"description","text":"都有婚姻不理想的一面更有婚姻不顺的征兆。"},{"type":"description","text":"有秉权好杀的一面。"},{"type":"description","text":"以能从事武职（公检法军警宪或武术教练）为佳。"},{"type":"description","text":"虽然具有魁罡的刚强性格，做任何事情，都要求圆满，但是他们也有敬老怜下，没有自负的精神，对于任何事，都会首先考虑别人立场和利益的特点。"},{"type":"description","text":"才能优秀，在单位上，容易受到上级的赏识和提拔，因此容易成功。"},{"type":"description","text":"但是多有遍游异乡、旅行、经商的征兆。"},{"type":"description","text":"在夫妻关系中，都是对方对自己实质性的爱，超过了自己对对方实质的性爱。"},{"type":"description","text":"和属鼠、属猴的人很合得来，大家在一起的心情很舒畅。"},{"type":"description","text":"能够激发自己的聪明才智，但也能促使自己目中无人。"},{"type":"description","text":"所以要警惕。"},{"type":"description","text":"和属虎、属兔的人也能交上朋友。"},{"type":"description","text":"属虎、属兔的人往往会给自己带来财运或者有关发财的信息。"},{"type":"description","text":"和属鸡的人也很合得来。"},{"type":"description","text":"但要注意，若自己正在恋爱中，和属鸡的人在一起，自己的恋爱，或者婚姻，则容易出现问题。"},{"type":"description","text":"若逢狗的大运、流年，则容易有乔迁之事发生，甚至出现职地之变。"},{"type":"description","text":"是太阳经被引动，容易引发生理上诸如头痛、胃病、小便清冷、消渴、胸胁腹痛、左臂、右腿寒病等症。"}]},"description":"根据日柱和性别动态查询命理分析（使用RizhuGenderAnalyzer适配器）"}],"rule_count":1,"message":null}%



不要用http 用rpc的通信协议，用谷歌的 Protocol Buffers (protobuf) 分析   jRpc 协议 。把 python 服务 打成二进制代码放上去  ，他应该看不到  。
日志加端口号  要不然分不清楚

方案2：gRPC + Protocol Buffers（推荐用于高性能）
使用 gRPC 框架 + protobuf
性能更好，但需要更多改造
适合：高性能、跨语言、内部微服务
