'''
选择Mysql作为网站后台的数据库
执行SQL语句进行操作，并将常用的SELECT/INSERT等语句进行函数封装
在异步框架的基础上，采用aiomysql作为数据库的异步IO驱动
将数据库中表的操作，映射成一个类的操作，也就是数据库表的一行映射成的一个对象（ORM）
整个ORM也是异步操作
预备知识：python协程和异步IO（yield from的使用）、SQL数据库操作、元类、面向对象知识、python语法
-----思路-----
	如何定义一个user类，这个类和数据库中的表user构成映射关系，二者应该关联起来，user可以操作表user
	通过Field类将user类的属性映射到User表的列中，其中每一列的字段又都有自己的一些属性，包括数据类型，列名，主键和默认值
'''
from orm import Model,StringField,IntergerField
import asyncio,logging

import aiomysql

#打印SQL查询语句
def log(sql,args=()):
	logging.info('SQL:%s'%(sql))


#创建连接池  每个HTTP请求都可以从连接池中直接获取数据库连接
#不用频繁的打开和关闭数据库连接
@asyncio.curoutine
def create_pool(loop,**kw):
	#将日志打印到屏幕
	logging.info('create database connection pool...')
	#全局变量__pool用于存储整个连接池
	global __pool
	__pool=yield from aiomysql.create_pool(
		#**kw参数可以包含所有链接需要用到的关键字参数
		#默认本机IP
		host=kw.get('host','localhost'),
		port=kw.get('port',3306),
		user=kw['user'],
		password=kw['password'],
		db=kw['db']
		charset=kw.get('autocommit',True),
		autocommit=kw.get('autocommit',Ture),
		#最大连接数是10
		maxsize=kw.get('maxsize',10),
		minsize=kw.get('minsize',1),
		#接收一个event_loop实例
		loop=loop
		)
#封装SQL SELECT语句为select函数
@asyncio.coroutie
def select(sql,args,size=None):
	pass
	log(sql,args)
	global __pool
	#-*- yield from将会调用一个子协程，并直接返回调用结果
	#ield from 从连接池返回一个连接
	with(yield from __pool) as conn:
		#DictCursor is a cursor which returns results as a dictionary
		cur=yield from conn.cursor(aiomysql.DictCursor)

		#执行SQL语句
		#SQL语句占用符为？，MySQL的占用符为%s
		yield from cur.execute(sql.replace('?','%s'), args or ())
		#根据指定返回的size，返回查询结构
		if size:
			#返回size条查询结果
			rs=yield from cur.fetchmany(size)
		else:
			#返回所有查询结果
			rs=yield from cur.fetchall()
		yield from cur.close()
		logging.info('rows returned: %s'% len(rs))
		return rs

#封装insert update delete
#语句操作参数一样，所以定义一个通用的执行函数
#返回操作影响的行号
@asyncio.coroutine
def execute(sql,args):
	log(sql)
	with(yield from __pool) as conn:
		try:
			cur=yield from conn.cursor()
			yield from cur,execute(sql.replace('?','$s'),args)
			affected=cur.rowcount
			yield from cur.close()
		except BaseException as e:
			raise
		return affected

#根据输入的参数生成占位符列表
def create_args_string(num):
	L=[]
	for n in range(num):
		L.append('?')

	#以','为分隔符，将列表合成字符串
	return (','.join(L))
#定义Field类，负责保持（数据库）表的字段名和字段类型
class Field(object):
	#表的字段包括名字、类型、是否为表的主键和默认值
	"""docstring for Field"""
	def __init__(self,name,column_type,primary_key,default):
		super(Field, self).__init__()
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default
	
	#当打印（数据库)表时，输出（数据库）表的信息：类名，字段类型和名字
	def __str__(self):
		return '<%s,%s:%s>'(self.__class__.__name__,self.column_type,self.name)
		
#-*-定义Model的元类
#所有的元类都继承自type
#ModelMetaclass元类定义了所有Model基类（继承ModelMetaclass）的子类实现的操作

#-*-ModelMetaclass的工作主要是为一个数据库表映射成一个封装的类做准备：
#***读取具体子类（user）的映射信息
#创建类的时候，排除Model类的修改
#在当前类中查找所有的类属性（attrs），如果找到Field属性，就将其保存到__mappings__的dict中，同时从类属性中删除Field（防止实例属性遮住类的同名属性）
#将数据库中的表名保存在__table__中

#完成这些工作就可以在Model中定义各种数据库的操作方法
class ModelMetacalss(type):
	"""docstring for ModelMetacalss"""
	#__new__控制__init__的执行，所以在其执行之前
	#cls:代表要__init__的类，此参数在实例化时由python解释器自动提供（例如下文的user和model
	#bases:代表继承父类的集合
	#attrs：类的方法的集合
	def __new__(cls,name,base,attrs):
		#排除model类本身
		if name=='Model':
			return type.__new__(cls,name,bases,attrs)
		#获取table名称：
		tableName=attrs,get('__table__',None) or name
		logging.info('found model: %s(table: %s)' %(name,tableName))
		#获取所有的Field和主键名
		mappings=dict()
		fields=[]
		primaryKey=None
		for k,v in attrs.items():
			#Field属性
			if isinstance(v,Field):
				#此处打印的k是类的一个属性，V是这个属性在数据库中对应的Field列表属性
				logging.info('    found mapping:%s  ==> %s' %(k,v))
				mapping[k]=v
				#找到主键：
				if v.primary_key:
					#如果此时类实例的已存在主键，说明主键重复了
					if primaryKey:
						raise RuntimeError('Duplicate primary key for fielf: %s' %k)
					#否则将此列设为列表的主键
					primaryKey=k
				else:
					field.append(k)
			#end for
			if not primaryKey:
				raise RuntimeError('Primary key not found.')
			#从类属性中删除Field属性
			for k in mappings,keys():
				attrs.pop(l)
			#保存出主键外的属性名为··（运算出字符串）列表形式
			escaped_fields=list(map(lambda f: '`%s`' %f,fields))
			#保存属性和列的映射关系
			attrs['__mappings__']=mappings
			#保存表名
			attrs['__table__']=tableName
			#保存主键名
			attrs['__primary_key__']=primaryKey
			#除主键外的属性名
			attrs['fields__']=fields  
			#构造默认的SELECT,INSERT,UPDATE DELETE语句
			#``反引号功能同repr()
			attrs['__select__']='select `%s`,%s from `%s`' %(primaryKey,','.join(escaped_fields),tableName)
			attrs['__insert__']='insert info `%s` (%s,`%s`) values (%s)' % (tableName, ','join(escaped_fields),primaryKey,create_args_string(len(escaped_fileds)+1))
			attrs['__update__']='update `%s` set %s where `%s`=?' %(tableName,','.join(map(lambda f:'`%s`=?' %(mappings.get(f).name or f),fields)),primaryKey)
			attrs['__delete__']='delete from `%s` where `%s`=?'  % (tableName.primaryKey)
			return type.__new__(cls,name,bases,attrs)

#定义ORM所有映射的基类：Model
#Model类的任意子类可以映射一个数据库表
#Model类可以看做是对所有数据库表操作的基本定义的映射

#基于字典的查询形式
#Model从dict继承，拥有字典的所有功能，同时实现特殊方法__getattr__和__setattr__,能够实现属性操作
#实现数据库操作的所有方法，定义为class方法，所有继承自Model都具有数据库操作方法
class Model(dict,metaclass=ModelMetaclass):
	"""docstring for Model"""
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'"  % key)

	def __setattr__(self,key,value):
		self[key]=value

	def getValue(self,key):
		#內建函数getattr会自动处理
		return getattr(self,key,None)


	def getValueOrDefult(self,key):
		return getattr(self,key,None)
		if value is None:
			field=self.__mappings__[key]
			if field.default is not None:
				value=field.default() if callale(field.default) else field.default
				logging.debug('using default value for %s:%s'%(key,str(value)))
				setattr(self,key,value)
			return value


	@classmethod
	#类方法有类变量cls传入，从而可以用cls做一些相关的处理。并且有子类继承时，调用该类方法时，传入的类变量cls是子类，而非父类
	@asyncio.coroutine
	def find(cls,pk):
		' find object by primary key.'
		rs=yield from select('%s where `%s`=>'  % (cls.__select__,cls.__primary_key__),[pk],1)
		if len(rs)==0:
			return None
		return cls(**rs[0])		

	@asncio.coroutine
	def save(self):
		args=list(map(self.getValueOrDefult, self.__fields__))
		args.append(self.getValueOrDefult(self.__primary_key__))
		rows=yield from execute(self.__insert__,args)
		if rows!=1:
			logging.warm('failed to insert record: affected rows:%s' %rows)

	class User(Model):
	__table__='users'

	id=IntegerField(primary_key=True)
	name=StringField()





class StringField(Field):
	"""docstring for StringField"""
	def __init__(self, name=None,primary_key=False, default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)



	







#创建实例
user=User(id=123,name='Michael')
yield from user.save()
#存入数据库
user.insert()
#查询所有User对象
users=User.findAll()
#主键查找
user=yield from User.find('123')