#!/usr/bin/env python3
"""
Fetch bibtex files from IFPB library for empty bibtex entries in ementario.json.
Uses ISBNs from reference text or provided table to search the Koha library system.
"""

import json
import re
import os
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMENTARIO_PATH = os.path.join(BASE_DIR, 'course/engenharia-de-software/ementas/ementario.json')
BIBTEX_DIR = os.path.join(BASE_DIR, 'course/engenharia-de-software/bibtex')
LIBRARY_BASE = 'https://biblioteca.ifpb.edu.br'

# Provided table: isbn13 -> isbn10 (from user's reference data)
TABLE_ISBN_MAP = {
    '9788576051152': '857605115X',
    '9788582602256': '8582602251',
    '9788522112586': '8522112584',
    '9788588639065': '8588639068',
    '9788521612599': '8521612591',
    '9788529400945': '8529400941',
    '9788577802708': '8577802701',
    '9788534603089': '8534603081',
    '9788535236996': '8535236996',
    '9788536502212': '8536502215',
    '9788575222508': '8575222503',
    '9788539903337': '8539903334',
    '9788576087434': '857608743X',
    '9788576050247': '8576050242',
    '9788535210194': '8535210199',
    '9788575224625': '857522462X',
    '9788502141650': '8502141651',
    '9788576050414': '8576050412',
    '9788520432006': '852043200X',
    '9788585351090': '8585351098',
    '9788521205128': '8521205120',
    '9788520420591': '8520420591',
    '9788599135068': '8599135066',
    '9788520421888': '8520421881',
    '9788580555332': '8580555337',
    '9788579361081': '8579361087',
    '9786500019506': '6500019504',
    '9788535248821': '853524882X',
    '9781848003026': '1848003021',
    '9783319051543': '3319051547',
    '9788535207460': '8535207465',
    '9780136061694': '0136061699',
    '9780073376189': '0073376183',
    '9788566250534': '8566250532',
    '9788576089391': '8576089394',
    '9788575226810': '8575226819',
    '9788576088035': '8576088037',
    '9788576088622': '8576088622',
    '9788566250053': '8566250052',
    '9788582601952': '8582601956',
    '9788575222898': '8575222899',
    '9788575224380': '8575224387',
    '9788522110537': '8522110530',
    '9788521615439': '8521615434',
    '9788543020532': '8543020530',
    '9788587918888': '8587918885',
    '9788521617419': '8521617410',
    '9788521612537': '8521612532',
    '9788577801909': '857780190X',
    '9788535215366': '8535215360',
    '9788540701427': '8540701421',
    '9788577804825': '8577804828',
    '9780074504093': '0074504096',
    '9788543002392': '8543002397',
    '9788587918918': '8587918915',
    '9788529402062': '8529402065',
    '9788521610656': '8521610653',
    '9788534614689': '8534614687',
    '9788534603102': '8534603103',
    '9788535283457': '8535283455',
    '9788535209266': '8535209263',
    '9786555584264': '6555584262',
    '9788534603485': '8534603480',
    '9788575223321': '8575223321',
    '9788563406613': '8563406612',
    '9788582600184': '8582600186',
    '9781118290279': '1118290275',
    '9781590282571': '1590282574',
    '9788535236996': '8535236996',
    '9780130284464': '0130284467',
    '9788528301816': '8528301818',
    '9780521585439': '0521585430',
    '9780521596756': '0521596750',
    '9780521283649': '0521283647',
    '9780521318372': '0521318378',
    '9788571130173': '8571130175',
    '9788571130272': '8571130272',
    '9788588456952': '8588456958',
    '9788586930188': '8586930180',
    '9781405080057': '1405080051',
    '9780521497053': '0521497051',
    '9788576089902': '8576089904',
    '9788575222485': '8575222481',
    '9786586110777': '6586110777',
    '9786586057089': '6586057086',
    '9788572540360': '8572540369',
    '9786586057393': '6586057396',
    '9788575226469': '8575226460',
    '9788560031528': '8560031529',
    '9788582600061': '8582600062',
    '9788543024974': '8543024978',
    '9788536504612': '8536504617',
    '9788573076103': '8573076100',
    '9788536504056': '8536504056',
    '9788536508320': '8536508329',
    '9788521616504': '8521616503',
    '9788534602372': '8534602379',
    '9788536519418': '853651941X',
    '9788536508337': '8536508337',
    '9788575222782': '8575222783',
    '9788575224724': '8575224727',
    '9788575224199': '8575224190',
    '9788575226193': '8575226193',
    '9788575225110': '8575225111',
    '9788576051121': '8576051125',
    '9781785887284': '1785887289',
    '9788561893200': '8561893206',
    '9788575224410': '8575224417',
    '9788565848916': '8565848914',
    '9788575164280': '8575164287',
    '9788535277821': '853527782X',
    '9788577808335': '8577808335',
    '9788522103591': '8522103593',
    '9780074504123': '0074504126',
    '9788540701694': '8540701693',
    '9788521617693': '8521617690',
    '9788586804922': '8586804924',
    '9788521622147': '8521622147',
    '9788522107445': '8522107440',
    '9788576055631': '8576055635',
    '9788576053576': '8576053578',
    '9788576081739': '8576081733',
    '9788574524085': '8574524085',
    '9788543004792': '8543004799',
    '9788536509266': '8536509260',
    '9788573938920': '8573938927',
    '9788535274332': '8535274332',
    '9788566250466': '856625046X',
    '9788535279849': '8535279849',
    '9788535226263': '8535226265',
    '9788535217537': '8535217533',
    '9788522457588': '8522457581',
    '9788535212730': '8535212736',
    '9788543025001': '8543025001',
    '9788595157330': '8595157332',
    '9788575224557': '8575224557',
    '9788536532684': '8536532688',
    '9788575225011': '8575225014',
    '9788535220179': '8535220178',
    '9788588639188': '8588639181',
    '9788576059240': '857605924X',
    '9788536501758': '8536501758',
    '9783662565087': '3662565080',
    '9780982368114': '0982368119',
    '9788522456215': '8522456216',
    '9788582600665': '8582600666',
    '9788522499700': '8522499705',
    '9788582601068': '8582601069',
    '9788571105577': '857110557X',
    '9788588456747': '8588456745',
    '9788572443098': '8572443096',
    '9788516027766': '8516027767',
    '9788515018895': '8515018896',
    '9788577260270': '8577260275',
    '9788555192555': '8555192552',
    '9788522107865': '8522107866',
    '9788521609490': '8521609493',
    '9788521617471': '852161747X',
    '9788577800575': '8577800571',
    '9788576050117': '8576050110',
    '9788521622109': '8521622104',
    '9788521618072': '8521618077',
    '9788524106439': '8524106433',
    '9788521622055': '8521622058',
    '9788587394477': '8587394479',
    '9788521617761': '8521617763',
    '9788583160076': '8583160074',
    '9788571104389': '8571104387',
    '9788511010572': '8511010572',
    '9788532639059': '8532639054',
    '9788531405754': '8531405750',
    '9788566250046': '8566250044',
    '9788575222171': '8575222171',
    '9788535287288': '8535287280',
    '9788575226421': '8575226428',
    '9788575227220': '857522722X',
    '9781839214110': '1839214112',
    '9781492076988': '1492076988',
    '9781430219569': '1430219564',
    '9781484256251': '1484256255',
    '9788573936964': '8573936967',
    '9788572540360': '8572540369',
    '9781091210097': '1091210098',
    '9781492053743': '1492053740',
    '9788535272741': '8535272747',
    '9788572540575': '8572540571',
    '9780124105126': '0124105122',
    '9781501121746': '150112174X',
    '9788597002881': '8597002883',
    '9788521617730': '8521617739',
    '9788582602218': '8582602219',
    '9788547220228': '8547220224',
    '9788502081062': '8502081063',
    '9788577804610': '8577804615',
    '9788522449897': '8522449899',
    '9788522104598': '852210459X',
    '9788536306674': '853630667X',
    '9788521602941': '8521602944',
    '9788576053705': '8576053705',
    '9788521614319': '8521614314',
    '9788573076516': '8573076518',
    '9788575221938': '8575221930',
    '9788566250114': '8566250117',
    '9788576081746': '8576081741',
    '9788588639287': '8588639289',
    '9788576053576': '8576053578',
    '9788535212723': '8535212728',
    '9788535236996': '8535236996',
    '9780132316811': '0132316811',
    '9780486485829': '048648582X',
    '9780201000290': '0201000296',
    '9780073523408': '0073523402',
    '9780716710455': '0716710455',
    '9780321295354': '0321295358',
    '9780201120370': '0201120372',
    '9788521616511': '8521616511',
    '9780470665763': '0470665769',
    '9780596008031': '0596008031',
    '9788535211207': '8535211209',
    '9788576089827': '8576089823',
    '9788579361098': '8579361095',
    '9788535264272': '8535264272',
    '9780321197863': '0321197860',
    '9788576088509': '8576088509',
    '9788576050476': '8576050471',
    '9788522458233': '8522458235',
    '9788524913112': '8524913118',
    '9788502160996': '8502160990',
    '9788502160965': '8502160966',
    '9788588456891': '8588456893',
    '9788575227268': '8575227262',
    '9788575226896': '8575226894',
    '9788575226902': '8575226908',
    '9788581436289': '8581436285',
    '9788575223444': '8575223445',
    '9788575223581': '8575223585',
    '9788521206033': '8521206038',
    '9781628251845': '1628251840',
    '9788535276152': '8535276157',
    '9788577809738': '8577809730',
    '9788521625735': '8521625731',
    '9780769551661': '0769551661',
    '9781628250138': '1628250135',
    '9788522490622': '8522490627',
    '9788574528816': '8574528811',
    '9780134000022': '0134000021',
    '9780132126953': '0132126958',
    '9780130464569': '0130464562',
    '9780937175729': '0937175722',
    '9788576089346': '8576089343',
    '9788555190438': '8555190436',
    '9781492087830': '1492087831',
    '9781098108304': '1098108302',
    '9788575223383': '8575223380',
    '9788582600481': '8582600488',
    '9788575224229': '8575224220',
    '9780124160446': '0124160441',
    '9781627052238': '1627052232',
    '9780262347037': '0262347032',
    '9788535206555': '8535206558',
    '9788536527000': '8536527005',
    '9788575226476': '8575226479',
    '9788582600535': '8582600534',
    '9781491950357': '1491950358',
    '9788576051268': '8576051265',
    '9788575222188': '857522218X',
    '9788576081715': '8576081717',
    '9788521618805': '8521618808',
    '9788550803814': '8550803812',
    '9788535237016': '8535237011',
    '9780070428072': '0070428077',
    '9786559773329': '6559773329',
    '9786559213085': '6559213080',
    '9788553219575': '8553219577',
    '9788502627239': '8502627236',
    '9786555594782': '6555594780',
    '9786555152531': '6555152532',
    '9788530991517': '8530991516',
    '9788522493395': '8522493391',
    '9788553219254': '8553219259',
    '9788522458561': '8522458561',
    '9788547220327': '8547220321',
    '9788575022337': '8575022334',
    '9788502032778': '8502032771',
    '9786587052083': '6587052088',
    '9788566103014': '8566103017',
    '9788577804818': '857780481X',
    '9788535252132': '8535252134',
    '9788575423387': '857542338X',
    '9788535264586': '8535264582',
    '9788522126682': '8522126682',
    '9788580553321': '8580553326',
    '9781473912144': '1473912148',
    '9788550804682': '8550804681',
    '9780470944882': '0470944889',
    '9781847197900': '1847197906',
    '9781633690714': '1633690717',
    '9781558605336': '1558605339',
    '9780596100162': '0596100167',
    '9780970601971': '0970601972',
    '9780970601988': '0970601980',
    '9781849693479': '1849693471',
    '9788561893088': '8561893087',
    '9788572515863': '8572515860',
    '9781138553590': '113855359X',
    '9781558608191': '1558608192',
    '9788543107165': '8543107164',
    '9788598582016': '8598582018',
    '9781492036739': '1492036730',
    '9781491979563': '1491979569',
    '9781491935675': '1491935677',
    '9781484262153': '1484262158',
    '9781492046905': '1492046906',
    '9788555191534': '855519153X',
    '9788572540247': '8572540245',
}


# Table-based lookup: (normalized_author, year) -> isbn13
# Built from user-provided table data
TABLE_REF_LOOKUP = {
    ('FLEMMING', '2006'): '9788576051152',
    ('HOWARD', '2014'): '9788582602256',
    ('STEWART', '2015'): '9788522112586',
    ('FINNEY', '2002'): '9788588639065',
    ('GUIDORIZZI', '2001'): '9788521612599',
    ('LEITHOLD', '1994'): '9788529400945',  # v.1
    ('ROGAWSKI', '2009'): '9788577802708',
    ('SWOKOWSKI', '1994'): '9788534603089',
    ('CORMEN', '2012'): '9788535236996',
    ('MANZANO', '2014'): '9788536502212',
    ('MENEZES', '2010'): '9788575222508',
    ('ALMEIDA', '2013'): '9788539903337',
    ('BARRY', '2012'): '9788576087434',
    ('FORBELLONE', '2005'): '9788576050247',
    ('LOPES', '2002'): '9788535210194',
    ('RAMALHO', '2015'): '9788575224625',
    ('BARBIERI', '2012'): '9788502141650',
    ('BRAGA', '2005'): '9788576050414',
    ('PHILIPPI', '2014'): '9788520432006',
    ('DIAS', '2004'): '9788585351090',
    ('MANO', '2010'): '9788521205128',
    ('MONTIBELLER', '2006'): '9788520420591',
    ('PAZ', '2006'): '9788599135068',
    ('PRESSMAN', '2016'): '9788580555332',
    ('SOMMERVILLE', '2011'): '9788579361081',
    ('VALENTE', None): '9786500019506',
    ('HIRAMA', '2012'): '9788535248821',
    ('JALOTE', '2008'): '9781848003026',
    ('MEYER', '2014'): '9783319051543',
    ('PETERS', '2001'): '9788535207460',
    ('PFLEEGER', '2010'): '9780136061694',
    ('SCHACH', '2011'): '9780073376189',
    ('AQUILES', '2014'): '9788566250534',
    ('DUCKETT', '2016'): '9788576089391',
    ('GRINBERG', '2018'): '9788575226810',
    ('CASTRO', '2013'): '9788576088035',
    ('FREEMAN', '2015'): '9788576088622',  # HTML e CSS
    ('MAZZA', '2013'): '9788566250053',
    ('MILETTO', '2014'): '9788582601952',
    ('SILVA', '2012'): '9788575222898',  # CSS3
    ('SILVA', '2015'): '9788575224380',  # Fundamentos HTML5
    ('FOROUZAN', '2011'): '9788522110537',
    ('MONTEIRO', '2011'): '9788521615439',
    ('STALLINGS', '2017'): '9788543020532',
    ('CAPRON', '2004'): '9788587918888',
    ('DALE', '2011'): '9788521617419',
    ('TANENBAUM', '2001'): '9788521612537',
    ('VAHID', '2008'): '9788577801909',
    ('VELLOSO', '2004'): '9788535215366',
    ('WEBER', '2012'): '9788540701427',
    ('SANTOS', '2009'): '9788577804825',
    ('STEINBRUCH', '1987'): '9780074504093',
    ('WINTERLE', '2014'): '9788543002392',
    ('BOULOS', '2004'): '9788587918918',
    ('LEITHOLD', '1994b'): '9788529402062',  # v.2
    ('REIS', '1996'): '9788521610656',
    ('SIMMONS', '1996'): '9788534614689',
    ('CELES', '2004'): '9788535283457',
    ('LAMBERT', '2022'): '9786555584264',
    ('TENENBAUM', '1995'): '9788534603485',
    ('BEAZLEY', '2013'): '9788575223321',
    ('CAVALCANTI', '2015'): '9788563406613',
    ('GOODRICH', '2013'): '9788582600184',
    ('MILLER', '2013'): '9781590282571',
    ('SHAFFER', '2001'): '9780130284464',
    ('BRONCKART', '1999'): '9788528301816',
    ('DOUGLAS', '2002'): '9780521585439',
    ('DUDLEY-EVANS', '2003'): '9780521596756',
    ('GRELLET', '2003'): '9780521283649',
    ('HUTCHINSON', '1987'): '9780521318372',
    ('KLEIMAN', '1996'): '9788571130173',
    ('DIOGENES', '2009'): '9788588456952',
    ('DIONISIO', '2003'): '9788586930188',
    ('NUTTAL', '1982'): '9781405080057',
    ('RICHARDS', '1998'): '9780521497053',
    ('FREEMAN', '2016'): '9788576089902',  # JavaScript
    ('SILVA', '2010'): '9788575222485',  # JavaScript guia
    ('ADRIANO', '2021'): '9786586110777',
    ('BROWN', '2020'): '9786586057089',
    ('MACHADO', '2021'): '9788572540360',  # Angular
    ('GUEDES', '2018'): '9788575226469',
    ('LARMAN', '2007'): '9788560031528',
    ('PREECE', '2013'): '9788582600061',
    ('SOMMERVILLE', '2019'): '9788543024974',
    ('FURGERI', '2013'): '9788536504612',
    ('GAMMA', '2000'): '9788573076103',
    ('LIMA', '2012'): '9788536504056',
    ('LIMA', '2014'): '9788536508320',
    ('PAULA', '2009'): '9788521616504',
    ('SBROCCO', '2012'): '9788536519418',
    ('SBROCCO', '2014'): '9788536508337',
    ('MOTA', '2012'): '9788575222782',
    ('NOAL', '2016'): '9788575224724',
    ('WARD', '2015'): '9788575224199',
    ('BRITO', '2017'): '9788575226193',
    ('MORENO', '2016'): '9788575225110',
    ('NEMETH', '2007'): '9788576051121',
    ('PELZ', '2016'): '9781785887284',
    ('RIBEIRO', None): '9788561893200',
    ('BROD', '2015'): '9788575224410',
    ('KOLLER', '2014'): '9788565848916',
    ('SOUSA', '2010'): '9788575164280',
    ('WAZLAWICK', '2014'): '9788535277821',
    ('LIPSCHUTZ', '2011'): '9788577808335',
    ('POOLE', '2014'): '9788522103591',
    ('ANTON', '2012'): '9788540701694',
    ('LEON', '2011'): '9788521617693',
    ('NICHOLSON', '2006'): '9788586804922',
    ('SHIFRIN', '2013'): '9788521622147',
    ('STRANG', '2010'): '9788522107445',
    ('DEITEL', '2010'): '9788576055631',
    ('HORSTMANN', '2009'): '9788576053576',
    ('SIERRA', '2007'): '9788576081739',
    ('COSTA', '2009'): '9788574524085',
    ('MANZANO', '2014b'): '9788536509266',
    ('SANTOS', '2010'): '9788573938920',
    ('SANTOS', '2013'): '9788535274332',
    ('SILVEIRA', '2014'): '9788566250466',
    ('DATE', '2004'): '9788535212730',
    ('ELMASRI', '2019'): '9788543025001',
    ('SILBERSCHATZ', '2020'): '9788595157330',
    ('DATE', '2015'): '9788575224557',
    ('MACHADO', '2020'): '9788536532684',
    ('NIELD', '2016'): '9788575225011',
    ('COMER', '2006'): '9788535220179',
    ('KUROSE', '2006'): '9788588639188',
    ('DUMAS', '2018'): '9783662565087',
    ('SILVER', '2011'): '9780982368114',
    ('VALLE', '2016'): '9788522456215',
    ('BROCKE', '2013'): '9788582600665',
    ('CRUZ', '2015'): '9788522499700',
    ('AZEREDO', '2000'): '9788571105577',
    ('MARCUSCHI', '2008'): '9788588456747',
    ('COSSON', '2006'): '9788572443098',
    ('LAJOLO', '2001'): '9788516027766',
    ('BAGNO', '1999'): '9788515018895',
    ('RAMAKRISHNAN', '2008'): '9788577260270',
    ('CARVALHO', '2017'): '9788555192555',
    ('ROB', '2010'): '9788522107865',
    ('MACHADO', '2011'): '9788521609490',  # SO fundamentos
    ('GALVIN', '2010'): '9788521617471',
    ('TANENBAUM', '2008'): '9788577800575',
    ('DEITEL', '2005'): '9788576050117',
    ('MACHADO', '2013'): '9788521622109',
    ('MARQUES', '2011'): '9788521618072',
    ('OLIVEIRA', '2004'): '9788524106439',
    ('ANTUNES', '2004'): '9788587394477',
    ('BARGER', '2011'): '9788521617761',
    ('HALL', '2015'): '9788583160076',
    ('LARAIA', '2009'): '9788571104389',
    ('MARTINS', '2001'): '9788511010572',
    ('SELL', '2015'): '9788532639059',
    ('MASIERO', '2008'): '9788531405754',
    ('ANICHE', '2012'): '9788566250046',
    ('ENGHOLM', '2010'): '9788575222171',
    ('MALDONADO', '2021'): '9788535287288',
    ('PERSIVAL', '2017'): '9788575226421',
    ('PIRES', '2017'): '9788575227220',
    ('CASCIARO', '2020'): '9781839214110',
    ('HECKLER', '2021'): '9781492076988',
    ('MIKE', '2009'): '9781430219569',
    ('LEONARD', '2020'): '9781484256251',
    ('MIKE', '2008'): '9788573936964',
    ('RAUSHMAYER', '2019'): '9781091210097',
    ('VANDERKAM', '2019'): '9781492053743',
    ('DIAS', '2013'): '9788535272741',
    ('GALVAO', '2020'): '9788572540575',
    ('RUNCO', '2014'): '9780124105126',
    ('KNAPP', '2016'): '9781501121746',
    ('PADUA', '2015'): '9788597002881',
    ('MARIANO', '2011'): '9788521617730',
    ('STUART', '2014'): '9788582602218',
    ('BUSSAB', '2017'): '9788547220228',
    ('CRESPO', '2009'): '9788502081062',
    ('SPIEGEL', '2009'): '9788577804610',
    ('BARBETTA', '2008'): '9788522449897',
    ('DEVORE', '2006'): '9788522104598',
    ('FREUND', '2006'): '9788536306674',
    ('MAYER', '2000'): '9788521602941',
    ('MORETTIN', '2010'): '9788576053705',
    ('TRIOLA', '2005'): '9788521614319',
    ('GUERRA', '2014'): '9788566250114',
    ('FREEMEN', '2009'): '9788576081746',
    ('PRESSMAN', '1995'): '9788534602372',
    ('ALUR', '2004'): '9788535212723',
    ('LEVITIN', '2011'): '9780132316811',
    ('AHO', '1974'): '9780201000290',
    ('DASGUPTA', '2006'): '9780073523408',
    ('GAREY', '1979'): '9780716710455',
    ('KLEINBERG', '2005'): '9780321295354',
    ('MANBER', '1989'): '9780201120370',
    ('FERREIRA', '2008'): '9788521616511',
    ('TIDWELL', '2011'): '9780596008031',
    ('BARBOSA', '2010'): '9788535211207',
    ('BEAIRD', '2008'): '9788576089827',
    ('BENYON', '2011'): '9788579361098',
    ('NIELSEN', '2014'): '9788535264272',
    ('SHNEIDERMAN', '2004'): '9780321197863',
    ('KRUG', '2014'): '9788576088509',
    ('CERVO', '2007'): '9788576050476',
    ('GIL', '2010'): '9788522458233',
    ('SEVERINO', '2008'): '9788524913112',
    ('AQUINO', '2012a'): '9788502160996',
    ('BORTONI-RICARDO', '2008'): '9788588456891',
    ('LEAL', '2019'): '9788575227268',
    ('LECHETA', '2018a'): '9788575226896',
    ('LECHETA', '2018b'): '9788575226902',
    ('NUDELMAN', '2013'): '9788575223581',
    ('KERZNER', '2011'): '9788521206033',
    ('PMI', '2017'): '9781628251845',
    ('HELDMAN', '2014'): '9788535276152',
    ('NOKES', '2011'): '9788577809738',
    ('SANTOS', '2014'): '9788521625735',
    ('SWEBOK', '2014'): '9780769551661',
    ('SWX', '2013'): '9781628250138',
    ('TRENTIN', '2014'): '9788522490622',
    ('VARGAS', '2014'): '9788574528816',
    ('SUEHRING', '2015'): '9780134000022',
    ('TOXEN', '2002'): '9780130464569',
    ('GARFINKEL', '1991'): '9780937175729',
    ('AMARAL', '2016'): '9788576089346',
    ('BOAGLIO', '2015'): '9788555190438',
    ('DENSMORE', '2021'): '9781492087830',
    ('HOUSLEY', '2022'): '9781098108304',
    ('SADALAGE', '2013'): '9788575223383',
    ('BAEZA-YATES', '2013'): '9788582600481',
    ('DAVID', '2015'): '9788575224229',
    ('DOAN', '2012'): '9780124160446',
    ('DONG', '2015'): '9781627052238',
    ('KELLEHER', '2018'): '9780262347037',
    ('KIMBAL', '2000'): '9788535206555',
    ('MACHADO', '2018'): '9788536527000',
    ('MCKINNEY', '2019'): '9788575226476',
    ('COULOURIS', '2013'): '9788582600535',
    ('NEWMAN', None): '9781491950357',
    ('BURKE', '2007'): '9788576051268',
    ('GOMES', '2010'): '9788575222188',
    ('RICHARDSON', '2007'): '9788576081715',
    ('FACELI', '2011'): '9788521618805',
    ('GERON', '2019'): '9788550803814',
    ('RUSSEL', '2013'): '9788535237016',
    ('MITCHELL', '1997'): '9780070428072',
    ('GABRIEL', '2022'): '9786559773329',
    ('ANDRADE', '2010'): '9788522458561',
    ('MATTAR', '2007'): '9788547220327',
    ('OLIVEIRA', '2008'): '9788575022337',
    ('CHIAVENATO', '2012'): '9788502032778',
    ('DORNELAS', '2021'): '9786587052083',
    ('DORNELAS', '2016'): '9788566103014',
    ('BESSANT', '2009'): '9788577804818',
    ('CAVALCANTI', '2011'): '9788535252132',
    ('DOLABELA', '2008'): '9788575423387',
    ('DRUCKER', '2016'): '9788522126682',
    ('HISRICH', '2014'): '9788580553321',
    ('KIRK', '2016'): '9781473912144',
    ('KNAFLIC', '2017'): '9788550804682',
    ('YAU', '2011'): '9780470944882',
    ('TOSI', '2009'): '9781847197900',
    ('BERINATO', '2016'): '9781633690714',
    ('CARD', '1999'): '9781558605336',
    ('FEW', '2016'): '9780596100162',
    ('FEW', '2012'): '9780970601971',
    ('FEW', '2009'): '9780970601988',
    ('KIRK', '2012'): '9781849693479',
    ('LEME', '2010'): '9788561893088',
    ('INMON', '2001'): '9788572515863',
    ('GRANT', '2018'): '9781138553590',
    ('WARE', '2004'): '9781558608191',
    ('DONEDA', '2020'): '9788553219575',
    ('OLIVEIRA', '2016'): '9788502627239',
    ('PINHEIRO', '2021'): '9786555594782',
    ('BARBOSA', '2021'): '9786555152531',
    ('LEMOS', '2014'): '9788522493395',
    ('MALDONADO', '2020'): '9788553219254',
    ('SCHWABER', '2019'): '9788543107165',
    ('WERKEMA', '2004'): '9788598582016',
    ('KANE', '2018'): '9781492036739',
    ('LASTER', '2018'): '9781491979563',
    ('BEDA', '2017'): '9781491935675',
    ('SABHARWAL', '2020'): '9781484262153',
    ('BRIKMAN', '2019'): '9781492046905',
    ('JULIAN', '2017'): '9781491957356',
    ('BOAGLIO', '2016'): '9788555191534',
    ('SANTOS', '2019'): '9788572540247',
    ('MATZAR', '2010'): '9788522458561',
}


class BiblionumberParser(HTMLParser):
    """Parse Koha search results to find biblionumber."""
    def __init__(self):
        super().__init__()
        self.biblionumbers = []
        self.in_result = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            href = attrs['href']
            match = re.search(r'biblionumber=(\d+)', href)
            if match:
                num = match.group(1)
                if num not in self.biblionumbers:
                    self.biblionumbers.append(num)


def extract_isbn_from_ref(ref):
    """Extract ISBN13 from reference text, trying various formats."""
    # Strategy: find any sequence of digits+hyphens that has exactly 13 digits and starts with 978/979
    # This handles: 9788535248821, 978-85-3524-882-1, 978-85-7608-939-1, etc.

    # Find all ISBN-like sequences (digits and hyphens together)
    candidates = re.findall(r'97[89][\d\-]{10,17}', ref)
    for c in candidates:
        digits = re.sub(r'[^0-9]', '', c)
        if len(digits) == 13:
            return digits

    # Also look for sequences after "ISBN" keyword
    isbn_matches = re.findall(r'ISBN[-\s:]*([0-9][\d\-\s]{10,18})', ref, re.I)
    for m in isbn_matches:
        digits = re.sub(r'[^0-9X]', '', m.upper())
        if len(digits) == 13 and digits[:3] in ('978', '979'):
            return digits
        if len(digits) == 10:
            converted = isbn10_to_13(digits)
            if converted:
                return converted

    # ISBN-10 pattern (after ISBN keyword)
    isbn10_match = re.search(r'ISBN[-:\s]*(\d{9}[\dX])', ref, re.I)
    if isbn10_match:
        return isbn10_to_13(isbn10_match.group(1))

    return None


def lookup_isbn_from_table(ref):
    """Try to find ISBN from the table by matching author last name + year in reference."""
    # Extract first significant word (usually last name of first author)
    ref_upper = ref.upper()
    first_word_match = re.match(r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ\-]+)', ref_upper)
    if not first_word_match:
        return None

    first_word = first_word_match.group(1)
    # Normalize accents
    replacements = {'Á':'A','À':'A','Â':'A','Ã':'A','Ä':'A',
                   'É':'E','È':'E','Ê':'E','Ë':'E',
                   'Í':'I','Ì':'I','Î':'I','Ï':'I',
                   'Ó':'O','Ò':'O','Ô':'O','Õ':'O','Ö':'O',
                   'Ú':'U','Ù':'U','Û':'U','Ü':'U',
                   'Ç':'C','Ñ':'N'}
    for k, v in replacements.items():
        first_word = first_word.replace(k, v)

    # Extract year
    years = re.findall(r'\b(19[0-9]{2}|20[0-2][0-9])\b', ref)

    # Try with each year found
    for year in years:
        key = (first_word, year)
        if key in TABLE_REF_LOOKUP:
            return TABLE_REF_LOOKUP[key]

    # Try without year
    key = (first_word, None)
    if key in TABLE_REF_LOOKUP:
        return TABLE_REF_LOOKUP[key]

    return None


def isbn10_to_13(isbn10):
    """Convert ISBN-10 to ISBN-13."""
    isbn10 = re.sub(r'[-\s]', '', isbn10)
    if len(isbn10) != 10:
        return None
    digits = '978' + isbn10[:9]
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    check = (10 - (total % 10)) % 10
    return digits + str(check)


def fetch_url(url, timeout=15):
    """Fetch URL content, following redirects."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace'), resp.geturl()
    except Exception as e:
        return None, None


def _parse_biblionumber(content, final_url):
    """Extract biblionumber from a Koha page (redirect or search results)."""
    if final_url and 'opac-detail.pl' in final_url:
        m = re.search(r'biblionumber=(\d+)', final_url)
        if m:
            return m.group(1)
    if content:
        parser = BiblionumberParser()
        parser.feed(content)
        if parser.biblionumbers:
            return parser.biblionumbers[0]
    return None


def search_library_by_isbn(isbn13):
    """Search IFPB library for a book by ISBN13. Returns biblionumber or None.

    Tries multiple Koha URL formats and both ISBN13/ISBN10.
    """
    isbn10 = TABLE_ISBN_MAP.get(isbn13)
    candidates = [isbn13] + ([isbn10] if isbn10 else [])

    for isbn in candidates:
        # Format 1: idx=isbn (direct ISBN index search — most reliable)
        url = f'{LIBRARY_BASE}/cgi-bin/koha/opac-search.pl?idx=isbn&q={isbn}'
        content, final_url = fetch_url(url)
        result = _parse_biblionumber(content, final_url)
        if result:
            return result

        # Format 2: q=isbn:ISBN (keyword prefix search)
        url2 = f'{LIBRARY_BASE}/cgi-bin/koha/opac-search.pl?q=isbn:{isbn}'
        content2, final_url2 = fetch_url(url2)
        result2 = _parse_biblionumber(content2, final_url2)
        if result2:
            return result2
        time.sleep(0.2)

    return None


def download_bibtex(biblionumber):
    """Download bibtex for a given biblionumber."""
    url = f'{LIBRARY_BASE}/cgi-bin/koha/opac-export.pl?op=export&bib={biblionumber}&format=bibtex'
    content, _ = fetch_url(url)
    return content


def generate_bib_key(bibtex_content, isbn13):
    """Generate a bib key like LASTNAME + YEAR from bibtex content."""
    author_match = re.search(r'author\s*=\s*\{([^}]+)\}', bibtex_content, re.I)
    year_match = re.search(r'year\s*=\s*\{(\d{4})', bibtex_content, re.I)

    if year_match:
        year = year_match.group(1)
    else:
        # Try to find any 4-digit year in the content (handles cases like c2012.)
        year_fallback = re.search(r'(19[0-9]{2}|20[0-2][0-9])', bibtex_content)
        year = year_fallback.group(1) if year_fallback else '0000'

    if author_match:
        author = author_match.group(1).strip()
        # Get first author's last name
        # Format could be "Lastname, Firstname" or "Firstname Lastname"
        parts = author.split(',')
        if len(parts) >= 2:
            lastname = parts[0].strip()
        else:
            # Try to get last word
            words = author.split()
            lastname = words[-1] if words else 'UNKNOWN'

        # Normalize: uppercase, remove accents and special chars
        lastname = lastname.upper()
        # Remove common accent chars
        replacements = {'Á':'A','À':'A','Â':'A','Ã':'A','Ä':'A',
                       'É':'E','È':'E','Ê':'E','Ë':'E',
                       'Í':'I','Ì':'I','Î':'I','Ï':'I',
                       'Ó':'O','Ò':'O','Ô':'O','Õ':'O','Ö':'O',
                       'Ú':'U','Ù':'U','Û':'U','Ü':'U',
                       'Ç':'C','Ñ':'N'}
        for k, v in replacements.items():
            lastname = lastname.replace(k, v)

        # Keep only alphanumeric
        lastname = re.sub(r'[^A-Z0-9]', '', lastname)
        if not lastname:
            lastname = 'UNKNOWN'
    else:
        lastname = 'UNKNOWN'

    return f'{lastname}{year}'


def format_bibtex(bibtex_content, key, isbn13, biblionumber):
    """Reformat bibtex with proper key, isbn, and url fields."""
    # Replace the auto-generated key (biblionumber) with proper key
    content = re.sub(r'@book\{[^,]+,', f'@book{{{key},', bibtex_content, count=1)

    # Remove trailing whitespace/braces issue
    content = content.strip()

    # Check if isbn field already exists
    if 'isbn' not in content.lower():
        isbn10 = TABLE_ISBN_MAP.get(isbn13, '')
        isbn_val = isbn13
        if isbn10:
            isbn_val = f'{isbn13}, {isbn10}'

        # Add isbn and url before closing brace
        detail_url = f'{LIBRARY_BASE}/cgi-bin/koha/opac-detail.pl?biblionumber={biblionumber}'
        content = content.rstrip().rstrip('}').rstrip()
        content += f',\n\tisbn = {{{isbn_val}}},\n\turl = {{{detail_url}}}\n}}'
    else:
        # Just add url if missing
        if 'url' not in content.lower():
            detail_url = f'{LIBRARY_BASE}/cgi-bin/koha/opac-detail.pl?biblionumber={biblionumber}'
            content = content.rstrip().rstrip('}').rstrip()
            content += f',\n\turl = {{{detail_url}}}\n}}'

    return content


def make_unique_key(key, existing_keys):
    """Make key unique by appending a letter suffix if needed."""
    if key not in existing_keys:
        return key
    # Try with letter suffixes
    for suffix in 'abcdefghijklmnopqrstuvwxyz':
        candidate = key + suffix
        if candidate not in existing_keys:
            return candidate
    return key + '_dup'


def main():
    os.makedirs(BIBTEX_DIR, exist_ok=True)

    with open(EMENTARIO_PATH, encoding='utf-8') as f:
        data = json.load(f)

    # Track existing bib keys and files
    existing_files = {f.replace('.bib', '') for f in os.listdir(BIBTEX_DIR) if f.endswith('.bib')}
    used_keys = set(existing_files)

    # Track ISBN → key for reuse across disciplines
    isbn_to_key = {}

    stats = {'total': 0, 'found': 0, 'not_found': 0, 'no_isbn': 0, 'already_exists': 0}

    for disc_idx, disc in enumerate(data):
        for bib_idx, bib in enumerate(disc.get('bibliografias', [])):
            if bib.get('bibtex') != []:
                continue

            stats['total'] += 1
            ref = bib['referencia']

            # Try to get ISBN (from text first, then from table lookup)
            isbn13 = extract_isbn_from_ref(ref)

            if not isbn13:
                isbn13 = lookup_isbn_from_table(ref)

            if not isbn13:
                print(f'  [NO ISBN] {ref[:80]}')
                stats['no_isbn'] += 1
                continue

            # Check if we already processed this ISBN
            if isbn13 in isbn_to_key:
                key = isbn_to_key[isbn13]
                bib_path = f'bibtex/{key}.bib'
                data[disc_idx]['bibliografias'][bib_idx]['bibtex'] = [bib_path]
                print(f'  [REUSE] {isbn13} → {key}.bib')
                stats['already_exists'] += 1
                continue

            # Check if a file already exists for this ISBN (check by scanning)
            existing_key = None
            bib_file_path = None
            for fname in os.listdir(BIBTEX_DIR):
                if not fname.endswith('.bib'):
                    continue
                fpath = os.path.join(BIBTEX_DIR, fname)
                try:
                    with open(fpath, encoding='utf-8') as f:
                        content = f.read()
                    if isbn13 in content:
                        existing_key = fname.replace('.bib', '')
                        break
                except:
                    pass

            if existing_key:
                isbn_to_key[isbn13] = existing_key
                bib_path = f'bibtex/{existing_key}.bib'
                data[disc_idx]['bibliografias'][bib_idx]['bibtex'] = [bib_path]
                print(f'  [EXISTS] {isbn13} → {existing_key}.bib')
                stats['already_exists'] += 1
                continue

            # Search library
            print(f'  [SEARCH] {isbn13} | {ref[:60]}...')
            biblionumber = search_library_by_isbn(isbn13)
            time.sleep(0.5)  # Rate limiting

            if not biblionumber:
                print(f'    → Not found in library')
                stats['not_found'] += 1
                continue

            # Download bibtex
            bibtex_raw = download_bibtex(biblionumber)
            time.sleep(0.3)

            if not bibtex_raw or '@book' not in bibtex_raw:
                print(f'    → Failed to download bibtex for biblionumber={biblionumber}')
                stats['not_found'] += 1
                continue

            # Generate key and format
            key = generate_bib_key(bibtex_raw, isbn13)
            key = make_unique_key(key, used_keys)
            used_keys.add(key)

            bibtex_formatted = format_bibtex(bibtex_raw, key, isbn13, biblionumber)

            # Save file
            bib_file = os.path.join(BIBTEX_DIR, f'{key}.bib')
            with open(bib_file, 'w', encoding='utf-8') as f:
                f.write(bibtex_formatted)

            isbn_to_key[isbn13] = key
            bib_path = f'bibtex/{key}.bib'
            data[disc_idx]['bibliografias'][bib_idx]['bibtex'] = [bib_path]

            print(f'    → Saved as {key}.bib (biblionumber={biblionumber})')
            stats['found'] += 1

        # Save progress periodically
        if (disc_idx + 1) % 5 == 0:
            with open(EMENTARIO_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'\n[Progress] Saved after discipline {disc_idx + 1}')

    # Final save
    with open(EMENTARIO_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'\n=== DONE ===')
    print(f'Total empty entries: {stats["total"]}')
    print(f'Found in library:    {stats["found"]}')
    print(f'Already existed:     {stats["already_exists"]}')
    print(f'Not found:           {stats["not_found"]}')
    print(f'No ISBN:             {stats["no_isbn"]}')


if __name__ == '__main__':
    main()
