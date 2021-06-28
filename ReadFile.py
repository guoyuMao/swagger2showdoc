import json

# swagger-json文件
base_file_path = r"out/{}.md"


# 一个请求的模版
one_path_format = """
#### 接口名

- ${summary}

##### 请求URL

- `${base_path}${path}`

##### 请求方式

- ${path_type}

##### contentType

- ${consumes}

##### 请求示例  
```
${request_json}

```
 
##### 请求参数

${request_params_head}
${request_parametes}
 
##### 返回示例  
```
${response_json}

``` 
 
##### 返回参数说明 

${response_values_head}
${response_values} 
 
##### 备注


"""

# 请求参数表格头格式，当不需要请求参数时不使用
request_params_head = """|索引|参数名|必选|类型|说明|
|:-----  |:-----  |:-----|-----|"""

# 请求参数
request_params_format = """|${index}|${name}| ${required} |  ${type} |  ${description} |\n"""

# 返回参数表格头格式，当不需要请求参数时不使用
response_values_head = """|参数名|类型|说明|
|:-----  |:-----|-----|"""
#返回数据
response_values_format = """|${index}|${name} |  ${type} |  ${description} |\n"""


def resolve_json(file_path):
    """
    解析json文件
    :param file_path: 文件
    :return:
    """
    file = open(file_path, "rb")
    file_json = json.load(file)

    project_info = file_json["info"]
    project_title = project_info["title"]
    host = file_json["host"]
    base_path = file_json["basePath"]
    tags = []
    for tag in file_json["tags"]:
        tags.append(tag["name"])

    paths = file_json["paths"]
    definitions = file_json["definitions"]

    return (project_title, host, base_path, paths,definitions)


def resolve_paths(base_path,paths,definitions):
    """
    解析paths 及 解析所有的请求
    :param base_path: 请求基础路径
    :param paths: 所有的请求
    :param definitions: 引用类信息
    :return:
    """
    for path in paths:
        # 解析各个接口
        path_info = paths[path]
        for path_type in path_info:
            # 每个接口可能有多个请求类型：GET\POST\PUT\PATCH\DELETE等
            path_type_info = path_info[path_type]
            # 解析接口的具体数据
            resolve_one_path(base_path,path_type_info,path_type,path,definitions)


def resolve_one_path(base_path,path_info,path_type,path,definitions):
    """
    解析一个接口的具体数据
    请求格式、请求头、请求参数、响应参数
    :param path_info:
    :return:
    """
    # 解析接口的具体数据
    tags = path_info["tags"]
    summary = path_info["summary"]
    consumes = path_info["consumes"]

    base_path = base_path if base_path != "/" else ""
    # 映射请求相关数据，将解析的数据放入模板中。
    one_path = one_path_format
    one_path = one_path.replace("${summary}", summary)
    one_path = one_path.replace("${base_path}", base_path)
    one_path = one_path.replace("${path}", path)
    one_path = one_path.replace("${path_type}", path_type)
    one_path = one_path.replace("${consumes}", consumes[0])

    # 处理请求参数
    if "parameters" in path_info:
        (req_rows,req_json) = hand_request_params(path_info, definitions)
        req_str = hand_rows(req_rows)
        one_path = one_path.replace("${request_params_head}", request_params_head)
        one_path = one_path.replace("${request_json}", json.dumps(req_json,ensure_ascii=False, indent=4))
        one_path = one_path.replace("${request_parametes}", req_str)
    else:
        # 不需要请求参数
        one_path = one_path.replace("${request_params_head}", "无")
        one_path = one_path.replace("${request_json}","")
        one_path = one_path.replace("${request_parametes}", "")

    # 处理返回值参数
    sources_responses = path_info["responses"]
    (resp_rows,resp_json) = hand_response_values(sources_responses, definitions)
    if type(resp_rows) == str:
        # 返回有一个简单类型的值
        one_path = one_path.replace("${response_values_head}", "")
        one_path = one_path.replace("${response_values}", resp_rows)
    else:
        #返回复杂类型（实体类、集合）或无返回
        if resp_rows:
            #有返回值
            one_path = one_path.replace("${response_values_head}", response_values_head)
            one_path = one_path.replace("${response_values}", hand_rows(resp_rows))
        else:
            one_path = one_path.replace("${response_values_head}", "无")
            one_path = one_path.replace("${response_values}", "")

    if resp_json:
        #有返回值
        one_path = one_path.replace("${response_json}", json.dumps(resp_json,ensure_ascii=False, indent=4))
    else:
        one_path = one_path.replace("${response_json}", "")

    #记录文件
    create_file(base_file_path.format(str(tags[0])), one_path)


def hand_rows(req_rows):
    req_str = ""
    if len(req_rows) > 0:
        for item in req_rows:
            if type(item) == list:
                req_str += hand_rows(item)
            else:
                req_str += item
    return req_str


def hand_response_values(responses,definitions):
    """
    解析请求参数
    :param responses: 响应信息
    :param definitions:  可能用的引用类
    :return: 解析后生成的文本数据
    """
    success_response = responses["200"]
    if "schema" in success_response:
        success_schema = success_response["schema"]
        if "$ref" in success_schema:
            # 解析引用类数据
            (child_rows,child_json) = hand_response_values_ref(definitions,success_schema,None)
            return (child_rows,child_json)
        else:
            # 非引用类型,则返回为一个简单类型数据
            response_value = response_values_format
            response_value = response_value.replace("${index}", "1")
            response_value = response_value.replace("${name}", "")

            type=""
            if "type" in success_schema:
                type = success_schema["type"]
            response_value = response_value.replace("${type}", type)

            description = ""
            if "description" in success_schema:
                description= success_schema["description"]
            response_value = response_value.replace("${description}", description)
            if type != "array":
                return (response_value, description if description != "" else type)  # 只有一个简单单的返回值，则返回该参数类型；

            else:
                # 参数为数组类型
                child_schema = success_schema["items"]
                if "$ref" in child_schema:
                    # 是引用类型
                    (child_rows, child_json) = hand_response_values_ref(definitions, child_schema, None)
                    response_value = response_value.replace("${type}", "Object")
                    list = []
                    list.append(child_json)
                    return (response_value,list)
                else:
                    type = child_schema["type"]
                    list = []
                    list.append(type)
                    response_value = response_value.replace("${type}", type)
                    return(response_value,list)

    else:
        # 返回值为空
        return (None,None)



def hand_response_values_ref(definitions, schema, super_index):
    """
    迭代解析引用参数
    :param definitions: 所用的引用类
    :param schema: 指向引用的关键信息
    :param super_index: 上一次的下标索引
    :return: resp_rows, resp_json
    """
    key = schema["$ref"].replace("#/definitions/", "")
    param = definitions.get(key)
    if param == None:
        # 没有在所有的引用类中找到需要的数据，则直接返回
        return
    properties = param["properties"]
    result_rows = []    #返回的数据集
    result_json = {}    #返回的json数据
    index = 0
    for pro in properties:
        index += 1
        # 解析每一个引用参数
        if super_index == None:
            index_str = str(index)
        else:
            index_str = super_index + "-" + str(index)
        response_value = response_values_format
        response_value = response_value.replace("${index}", index_str)
        response_value = response_value.replace("${name}", pro)

        pro_info = properties[pro]  # 字段的详细说明
        type = ""
        if "type" in pro_info:
            type = pro_info["type"]
        response_value = response_value.replace("${type}", type)

        description = ""
        if "description" in pro_info:
            description = pro_info["description"]
        response_value = response_value.replace("${description}", description)

        child_rows=[]
        child_json={}
        if "array" == type:
            # 引用数据-继续解析
            child_schema = pro_info["items"]
            if "$ref" in child_schema:
                # 是引用类型
                type = child_schema["$ref"].replace("#/definitions/", "")
                (child_rows,child_json)= hand_response_values_ref(definitions, child_schema, index_str)
            response_value = response_value.replace("${type}", type)
            result_rows.append(response_value)
            arr = []
            if child_rows:
                result_rows.append(child_rows)

            if child_json:
                arr.append(child_json)
            else:
                arr.append(description if description else type)  # 转化为列表数据
            result_json[pro] = arr

        else:
            if "$ref" in pro_info:
                # 引用参数迭代解析
                (child_rows, child_json)= hand_response_values_ref(definitions, pro_info, index_str)
                response_value = response_value.replace("${type}", "Object") # 从详细信息中获取字段类型

            result_rows.append(response_value)
            if child_rows:
                result_rows.append(child_rows)

            if child_json:
                result_json[pro] = child_json
            else:
                result_json[pro] = description
    return (result_rows,result_json)


def hand_request_params(path_type_info,definitions):
    """
    解析请求参数
    :param path_type_info: 一个请求的详细信息
    :return: 请求数据字段说明,各个字段的具体解释
    """
    parameters = path_type_info.get("parameters")   # 请求参数
    result_rows = []    #返回表格数据的一行
    result_json = {}   #返回的json格式数据
    index = 0
    for parameter in parameters:
        index += 1
        name = parameter["name"]
        description = parameter["description"]
        required = parameter["required"]

        req_params = request_params_format
        req_params = req_params.replace("${index}", str(index))
        req_params = req_params.replace("${name}", name)
        req_params = req_params.replace("${required}", str(required))
        req_params = req_params.replace("${description}", description)
        type = "" #字段类型
        if "type" in parameter:
            #如果是引用类型则type字段不存在
            type = parameter["type"]

        if "array" == type:
            # 参数类型为列表
            child_rows = None
            child_json = None
            items = parameter["items"] #array类型具体的数据
            if "type" in items:
                #简单类型
                type = items["type"]
                child_json = {}
            elif "$ref" in items:
                #引用类型
                (child_rows, child_json) = hand_request_params_ref(definitions, items, str(index))

            req_params = req_params.replace("${type}", type)
            result_rows.append(req_params)
            arr = []
            if child_rows:
                result_rows.append(child_rows)  #转化为列表数据
            if child_json:
                arr.append(child_json)
            else:
                arr.append(description if description else type)
            result_json[name] = arr  # 转化为列表数据
        else :
            #非数组类型
            child_rows = []
            child_json = {}
            if "schema" in parameter:
                # 引用类型参数
                schema = parameter["schema"]
                ref = schema["$ref"]
                type = ref.replace("#/definitions/", "")
                # 解析引用的参数
                (child_rows,child_json)= hand_request_params_ref(definitions, schema, str(index))

            req_params = req_params.replace("${type}", type)
            result_rows.append(req_params)
            if child_rows:
                result_rows.append(child_rows)

            if child_json:
                result_json[name] = child_json
            else:
                result_json[name] = description

    return (result_rows,result_json)


def hand_request_params_ref(definitions,schema,super_index):
    """
    迭代解析引用参数
    :param definitions: 所用的引用类
    :param schema: 指向引用的关键信息
    :param super_index: 上一次的下标索引
    :return: value:具体的值
    """
    result_rows = []
    result_json = {}

    key = schema["$ref"].replace("#/definitions/", "")
    param = definitions.get(key)

    if param == None:
        # 没有在所有的引用类中找到需要的数据，则直接返回
        return (result_rows,result_json)

    properties = param["properties"]
    index = 0
    for pro in properties:
        # 解析每一个引用参数
        index += 1
        index_str = super_index + "-" + str(index)
        request_params = request_params_format
        request_params = request_params.replace("${index}", index_str)
        request_params = request_params.replace("${name}", pro)

        pro_info = properties[pro] #字段的详细说明
        if "required" in pro_info:
            request_params = request_params.replace("${required}", str(pro_info.get("required")))
        else:
            request_params = request_params.replace("${required}", "false")

        description=""
        if "description" in pro_info:
            description = pro_info["description"]

        request_params = request_params.replace("${description}", description)

        this_type =""
        if "type" in pro_info:
            this_type = pro_info["type"]

        child_rows = None
        child_json = None
        if "items" in pro_info:
            # 数组类型数据
            child_schema = pro_info["items"]
            if "$ref" in child_schema:
                #是引用类型
                this_type = child_schema["$ref"].replace("#/definitions/", "")
                (child_rows,child_json) = hand_request_params_ref(definitions,child_schema, index_str)

            request_params = request_params.replace("${type}", this_type)
            result_rows.append(request_params)
            arr = []
            if child_rows:
                result_rows.append(child_rows)
            if child_json:
                arr.append(child_json)
            else:
                arr.append(description if description else this_type)  # 转化为列表数据
            result_json[pro] = arr
        else:
            #非数组类型
            if "$ref" in pro_info:
                # 引用参数迭代解析
                this_type = pro_info["$ref"].replace("#/definitions/", "")
                (child_rows, child_json) = hand_request_params_ref(definitions, pro_info, index_str)

            request_params = request_params.replace("${type}", this_type)
            result_rows.append(request_params)
            if child_rows:
                result_rows.append(child_rows)

            if child_json:
                result_json[pro] = child_json
            else:
                result_json[pro] = description

    return (result_rows,result_json)


def create_file(file_name,str):
    """
    生成文档
    :param file_name: 文件名
    :param str: 文件内容
    :return:
    """
    try:
        with open(file_name, "a+", encoding="utf-8") as testOne:
            testOne.write("\r\n")
            testOne.write("\r\n")
            testOne.write(str)
    except FileNotFoundError:
        print("not found file")
    except LookupError:
        print("指定了未知编码")
    except UnicodeDecodeError:
        print("读取文件时解码错误")

if __name__ == '__main__':
    file_path = r"file/test.json"
    (project_title, host, base_path,paths, definitions) = resolve_json(file_path)
    resolve_paths(base_path,paths,definitions)