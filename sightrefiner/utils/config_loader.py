import os


def ConfigLoader(configFileRoot, configFileName, configParser):
    filePath = os.path.join(configFileRoot, configFileName)
    configParser.read(filePath)
    print("===================== Configure Topics =====================")
    print(list(configParser))
    print("============================================================")
    return configParser


def TopicValueExtractor(configParser, topic, key):
    value = configParser.get(topic, key)
    return value


if __name__ == "__main__":
    import configparser

    configParser = configparser.ConfigParser()
    configFileRoot = "../data/"
    configFileName = "config.conf"
    configParser = ConfigLoader(configFileRoot, configFileName, configParser)
    print(
        "ProblemSummary", "Description", TopicValueExtractor(configParser, "ProblemSummary", "Description"), sep=" ==> "
    )

    labeledDict = {}
    labelExposed = int(TopicValueExtractor(configParser, "LabelDefinition", "Exposed"))
    repoExposed = TopicValueExtractor(configParser, "DataLoader", "ExposedRepo")
    labelOccluded = int(TopicValueExtractor(configParser, "LabelDefinition", "Occluded"))
    repoOccluded = TopicValueExtractor(configParser, "DataLoader", "OccludedRepo")
    labeledDict[labelExposed] = [
        os.path.join(configFileRoot, repoExposed, d) for d in os.listdir(os.path.join(configFileRoot, repoExposed))
    ]
    labeledDict[labelOccluded] = [
        os.path.join(configFileRoot, repoOccluded, d) for d in os.listdir(os.path.join(configFileRoot, repoOccluded))
    ]
    print(labeledDict)
