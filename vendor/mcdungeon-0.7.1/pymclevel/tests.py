'''
Created on Jul 23, 2011

@author: Rio
'''
#from mclevel import fromFile, loadWorldNumber, BoundingBox
#from infiniteworld import MCInfdevOldLevel
#from schematic import MCSchematic
#import errorreporting # annotate tracebacks with call arguments
try:
    from pymclevel import *
except ImportError:
    from __init__ import *

import itertools
import traceback
import unittest
import tempfile
import logging
import shutil
import os
from os.path import join
import time

import numpy
from numpy import *
from infiniteworld import MCServerChunkGenerator

log = logging.getLogger(__name__)
warn, error, info, debug = log.warn, log.error, log.info, log.debug

#logging.basicConfig(format=u'%(levelname)s:%(message)s')
#logging.getLogger().level = logging.INFO
def mktemp(suffix):
    td = tempfile.mkdtemp(suffix)
    os.rmdir(td)
    return td

class TempLevel(object):
    def __init__(self, filename, createFunc = None):
        if not os.path.exists(filename):
            filename = join("testfiles", filename)
        tmpname = mktemp(os.path.basename(filename))
        if os.path.exists(filename):
            if os.path.isdir(filename):
                shutil.copytree(filename, tmpname)
            else:
                shutil.copy(filename, tmpname)
        else:
            createFunc(tmpname)
        self.tmpname = tmpname
        self.level = fromFile(tmpname)

    def __del__(self):
        self.level.close()
        del self.level
        filename = self.tmpname

        if os.path.isdir(filename):
            shutil.rmtree(filename)
        else:
            os.unlink(filename)

class TestNBT(unittest.TestCase):
        
    def testLoad(self):
        "Load an indev level."
        level = nbt.load("testfiles/hell.mclevel");
    
        """The root tag must have a name, and so must any tag within a TAG_Compound"""
        print level.name
    
        """Use the [] operator to look up subtags of a TAG_Compound."""
        print level["Environment"]["SurroundingGroundHeight"].value;
    
    
        """Numeric, string, and bytearray types have a value 
        that can be accessed and changed. """
        print level["Map"]["Blocks"].value
    
        return level;
    
    def testCreate(self):
        "Create an indev level."
    
        "The root of an NBT file is always a TAG_Compound."
        level = TAG_Compound(name="MinecraftLevel")
    
        "Subtags of a TAG_Compound are automatically named when you use the [] operator."
        level["About"] = TAG_Compound()
        level["About"]["Author"] = TAG_String("codewarrior")
    
        level["Environment"] = TAG_Compound()
        level["Environment"]["SkyBrightness"] = TAG_Byte(16)
        level["Environment"]["SurroundingWaterHeight"] = TAG_Short(32)
    
        "You can also create and name a tag before adding it to the compound."
        spawn = TAG_List((TAG_Short(100), TAG_Short(45), TAG_Short(55)))
        spawn.name = "Spawn"
    
        mapTag = TAG_Compound()
        mapTag.add(spawn);
        mapTag.name = "Map"
        level.add(mapTag)
    
        "I think it looks more familiar with [] syntax."
    
        l, w, h = 128, 128, 128
        mapTag["Height"] = TAG_Short(h) # y dimension
        mapTag["Length"] = TAG_Short(l) # z dimension
        mapTag["Width"] = TAG_Short(w) # x dimension
    
        "Byte arrays are stored as numpy.uint8 arrays. "
    
        mapTag["Blocks"] = TAG_Byte_Array()
        mapTag["Blocks"].value = zeros(l * w * h, dtype=uint8) #create lots of air!
    
        "The blocks array is indexed (y,z,x) for indev levels, so reshape the blocks"
        mapTag["Blocks"].value.shape = (h, l, w);
    
        "Replace the bottom layer of the indev level with wood"
        mapTag["Blocks"].value[0, :, :] = 5;
    
        "This is a great way to learn the power of numpy array slicing and indexing."
        
        mapTag["Data"] = TAG_Byte_Array()
        mapTag["Data"].value = zeros(l * w * h, dtype=uint8)
    
        return level;
    
    def testModify(self):
        level = self.testCreate();
    
        "Most of the value types work as expected. Here, we replace the entire tag with a TAG_String"
        level["About"]["Author"] = TAG_String("YARRR~!");
    
        "Because the tag type usually doesn't change, "
        "we can replace the string tag's value instead of replacing the entire tag."
        level["About"]["Author"].value = "Stew Pickles"
    
        "Remove members of a TAG_Compound using del, similar to a python dict."
        del(level["About"]);
    
        "Replace all of the wood blocks with gold using a boolean index array"
        blocks = level["Map"]["Blocks"].value
        blocks[blocks == 5] = 41;
    
    
    def testSave(self):
    
        level = self.testCreate()
        level["Environment"]["SurroundingWaterHeight"].value += 6;
    
        "Save the entire TAG structure to a different file."
        atlantis = TempLevel("atlantis.mclevel", createFunc = level.save)
        
    
    def testErrors(self):
        """
        attempt to name elements of a TAG_List
        named list elements are not allowed by the NBT spec, 
        so we must discard any names when writing a list.
        """
    
        level = self.testCreate();
        level["Map"]["Spawn"][0].name = "Torg Potter"
        sio = StringIO()
        level.save(buf=sio)
        newlevel = nbt.load(buf=sio.getvalue())
    
        n = newlevel["Map"]["Spawn"][0].name
        if(n): print "Named list element failed: %s" % n;
        
        """
        attempt to delete non-existent TAG_Compound elements
        this generates a KeyError like a python dict does.
        """
        level = self.testCreate();
        try:
            del level["DEADBEEF"]
        except KeyError:
            pass
        else:
            assert False
    
    def testSpeed(self):
        d = join("testfiles", "TileTicks_chunks")
        files = [join(d, f) for f in os.listdir(d)]
        startTime = time.time()
        for i in range(20):
            for f in files[:40]:
                n = nbt.load(f)
        print "Duration: ", time.time() - startTime
        #print "NBT: ", n
        
class TestIndevLevel(unittest.TestCase):
    def setUp(self):
        self.srclevel = TempLevel("hell.mclevel")
        self.indevlevel = TempLevel("hueg.mclevel")

    def testEntities(self):
        level = self.indevlevel.level
        entityTag = Entity.Create("Zombie")
        tileEntityTag = TileEntity.Create("Painting")
        level.addEntity(entityTag)
        level.addTileEntity(tileEntityTag)
        schem = level.extractSchematic(level.bounds)
        level.copyBlocksFrom(schem, schem.bounds, (0, 0, 0))

        #raise Failure 

    def testCopy(self):
        info("Indev level")
        indevlevel = self.indevlevel.level
        srclevel = self.srclevel.level
        indevlevel.copyBlocksFrom(srclevel, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        assert((indevlevel.Blocks[0:64, 0:64, 0:64] == srclevel.Blocks[0:64, 0:64, 0:64]).all())

    def testFill(self):
        indevlevel = self.indevlevel.level
        indevlevel.fillBlocks(BoundingBox((0, 0, 0), (64, 64, 64,)), indevlevel.materials.Sand, [indevlevel.materials.Stone, indevlevel.materials.Dirt])
        indevlevel.saveInPlace()


class TestJavaLevel(unittest.TestCase):
    def setUp(self):
        self.creativelevel = TempLevel("Dojo_64_64_128.dat")
        self.indevlevel = TempLevel("hell.mclevel")

    def testCopy(self):
        indevlevel = self.indevlevel.level
        creativelevel = self.creativelevel.level

        creativelevel.copyBlocksFrom(indevlevel, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        assert(numpy.array((indevlevel.Blocks[0:64, 0:64, 0:64]) == (creativelevel.Blocks[0:64, 0:64, 0:64])).all())

        creativelevel.saveInPlace()
        #xxx old survival levels


class TestAlphaLevelCreate(unittest.TestCase):
    def testCreate(self):
        temppath = mktemp("AlphaCreate")
        self.alphaLevel = MCInfdevOldLevel(filename=temppath, create=True);
        self.alphaLevel.close()
        shutil.rmtree(temppath)
        
class TestAlphaLevel(unittest.TestCase):
    def setUp(self):
        #self.alphaLevel = TempLevel("Dojo_64_64_128.dat")
        self.indevlevel = TempLevel("hell.mclevel")
        self.alphalevel = TempLevel("PyTestWorld")

    def testUnsetProperties(self):
        level = self.alphalevel.level
        del level.root_tag['Data']['LastPlayed']
        import time
        level.LastPlayed
        level.LastPlayed = time.time() * 1000 - 1000000

    def testGetEntities(self):
        level = self.alphalevel.level
        print len(level.getEntitiesInBox(level.bounds))

    def testCreateChunks(self):
        indevlevel = self.indevlevel.level
        level = self.alphalevel.level

        for ch in list(level.allChunks): level.deleteChunk(*ch)
        level.createChunksInBox(BoundingBox((0, 0, 0), (32, 0, 32)))

    def testCopyConvertBlocks(self):
        indevlevel = self.indevlevel.level
        level = self.alphalevel.level
        level.copyBlocksFrom(indevlevel, BoundingBox((0, 0, 0), (256, 128, 256)), (-0, 0, 0))

        convertedSourceBlocks, convertedSourceData = indevlevel.convertBlocksFromLevel(level, indevlevel.Blocks[0:16, 0:16, 0:indevlevel.Height], indevlevel.Data[0:16, 0:16, 0:indevlevel.Height])
        assert (level.getChunk(0, 0).Blocks[0:16, 0:16, 0:indevlevel.Height] == convertedSourceBlocks).all()

    def testImportSchematic(self):
        indevlevel = self.indevlevel.level
        level = self.alphalevel.level

        schem = fromFile("schematics/CreativeInABox.schematic");
        level.copyBlocksFrom(schem, BoundingBox((0, 0, 0), (1, 1, 3)), (0, 64, 0));
        schem = MCSchematic(shape=(1, 1, 3))
        schem.copyBlocksFrom(level, BoundingBox((0, 64, 0), (1, 1, 3)), (0, 0, 0));
        convertedSourceBlocks, convertedSourceData = schem.convertBlocksFromLevel(level, schem.Blocks, schem.Data)
        assert (level.getChunk(0, 0).Blocks[0:1, 0:3, 64:65] == convertedSourceBlocks).all()

    def testRecreateChunks(self):
        level = self.alphalevel.level

        for x, z in itertools.product(xrange(-1, 3), xrange(-1, 2)):
            level.deleteChunk(x, z);
            level.createChunk(x, z)

    def testFill(self):
        level = self.alphalevel.level

        level.fillBlocks(BoundingBox((-11, 0, -7), (38, 128, 25)) , level.materials.WoodPlanks);
        c = level.getChunk(0, 0)
        assert (c.Blocks == 5).all()

    def testReplace(self):
        level = self.alphalevel.level

        level.fillBlocks(BoundingBox((-11, 0, -7), (38, 128, 25)) , level.materials.WoodPlanks, [level.materials.Dirt, level.materials.Grass]);

    def testSaveRelight(self):
        indevlevel = self.indevlevel.level
        level = self.alphalevel.level

        cx, cz = -3, -1;

        level.deleteChunk(cx, cz);

        level.createChunk(cx, cz);
        level.copyBlocksFrom(indevlevel, BoundingBox((0, 0, 0), (32, 64, 32,)), (-96, 32, 0))

        level.generateLights();
        level.saveInPlace();
    
    def testRecompress(self):
        cx,cz = -3, -1
        level = self.alphalevel.level
        ch = level.getChunk(cx,cz)
        ch.dirty = True
        level.saveInPlace()
        ch.Blocks
        print ch.root_tag
        
    def testPlayerSpawn(self):
        level = self.alphalevel.level

        level.setPlayerSpawnPosition((0, 64, 0), "Player")
        level.getPlayerPosition()
        level.players

class TestSchematics(unittest.TestCase):
    def setUp(self):
        #self.alphaLevel = TempLevel("Dojo_64_64_128.dat")
        self.indevlevel = TempLevel("hell.mclevel")
        self.alphalevel = TempLevel("PyTestWorld")

    def testCreate(self):
        #info("Schematic from indev")

        size = (64, 64, 64)
        temp = mktemp("testcreate.schematic")
        schematic = MCSchematic(shape=size, filename=temp, mats='Classic');
        level = self.indevlevel.level

        self.failUnlessRaises(ValueError, lambda:(
            schematic.copyBlocksFrom(level, BoundingBox((-32, -32, -32), (64, 64, 64,)), (0, 0, 0))
        ))

        schematic.copyBlocksFrom(level, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        assert((schematic.Blocks[0:64, 0:64, 0:64] == level.Blocks[0:64, 0:64, 0:64]).all())
        schematic.compress();

        schematic.copyBlocksFrom(level, BoundingBox((0, 0, 0), (64, 64, 64,)), (-32, -32, -32))
        assert((schematic.Blocks[0:32, 0:32, 0:32] == level.Blocks[32:64, 32:64, 32:64]).all())

        schematic.compress();

        schematic.saveInPlace();

        schem = fromFile("schematics/CreativeInABox.schematic");
        tempSchematic = MCSchematic(shape=(1, 1, 3))
        tempSchematic.copyBlocksFrom(schem, BoundingBox((0, 0, 0), (1, 1, 3)), (0, 0, 0))

        info("Schematic from alpha")
        level = loadWorldNumber(1)
        for cx, cz in itertools.product(xrange(0, 4), xrange(0, 4)):
            try:
                level.createChunk(cx, cz)
            except ValueError:
                pass
        schematic.copyBlocksFrom(level, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        schematic.close()
        os.remove(temp)
        
    def testRotate(self):
        level = self.indevlevel.level
        schematic = level.extractSchematic(level.bounds)
        schematic.rotateLeft()
        schematic.flipNorthSouth()
        schematic.flipVertical()

    def testZipSchematic(self):
        level = self.alphalevel.level
        box = BoundingBox((0, 0, 0), (64, 64, 64,))
        zs = level.extractZipSchematic(box)
        assert(box.chunkCount == zs.chunkCount)
        zs.close()
        os.remove(zs.filename)
        
    def testINVEditChests(self):
        info("INVEdit chest")
        invFile = fromFile("schematics/Chests/TinkerersBox.inv");
        info("Blocks: %s", invFile.Blocks)
        info("Data: %s", invFile.Data)
        info("Entities: %s", invFile.Entities)
        info("TileEntities: %s", invFile.TileEntities)
        #raise SystemExit;

class TestPocket(unittest.TestCase):
    def setUp(self):
        #self.alphaLevel = TempLevel("Dojo_64_64_128.dat")
        self.level = TempLevel("PocketWorld")
        self.alphalevel = TempLevel("PyTestWorld")
        
    def testPocket(self):
        level = self.level.level
#        alphalevel = self.alphalevel.level
        print "Chunk count", len(level.allChunks)
        chunk = level.getChunk(1,5)
        a = array(chunk.SkyLight)
        level.saveInPlace()
        assert (a == chunk.SkyLight).all()
        
#        level.copyBlocksFrom(alphalevel, BoundingBox((0, 0, 0), (64, 64, 64,)), (0, 0, 0))
        #assert((level.Blocks[0:64, 0:64, 0:64] == alphalevel.Blocks[0:64, 0:64, 0:64]).all())
        
        
class TestServerGen(unittest.TestCase):
    def setUp(self):
        #self.alphaLevel = TempLevel("Dojo_64_64_128.dat")
        self.alphalevel = TempLevel("PyTestWorld")
    
    def testCreate(self):
        gen = MCServerChunkGenerator()
        print "Version: ", gen.serverVersion
        
        def _testCreate(filename):
            gen.createLevel(filename, BoundingBox((-128, 0, -128), (128, 128, 128)))
            
        t = TempLevel("ServerCreate", createFunc=_testCreate)
        
    def testServerGen(self):
        gen = MCServerChunkGenerator()
        print "Version: ", gen.serverVersion

        level = self.alphalevel.level

        gen.generateChunkInLevel(level, 50, 50)
        gen.generateChunksInLevel(level, [(120, 50), (121, 50), (122, 50), (123, 50), (244, 244), (244, 245), (244, 246)])

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
