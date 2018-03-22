var args = process.argv.slice(2);

var inputFile = args[0]
var outFilename = args[1]

console.log("inputFile: " + inputFile);
console.log("outFilename: " + outFilename);
ReadSave(inputFile, outFilename)






function ReadSave(inputFile, outFilename) {
    var fs = require('fs'),
        path = require('path')
    console.log("ReadSave")
    fs.readFile(inputFile, { encoding: 'utf-8' }, function(err, data) {
        if (!err) {
            var saveData = EnterpretSave(data);
            SaveJsonFile(saveData, outFilename);
        } else {
            console.log(err);
        }
    });
}




function EnterpretSave(data) {
    console.log("EnterpretSave")
    var jomini = require('jomini');
    var parsed = jomini.parse(data);
    return parsed
}

function SaveJsonFile(jsonData, filename) {
    console.log("SaveJsonFile")
    var fs = require('fs')

    fs.writeFile(filename, JSON.stringify(jsonData), function(err) {
        if (err) {
            // console.log(err);
        }
    });
}