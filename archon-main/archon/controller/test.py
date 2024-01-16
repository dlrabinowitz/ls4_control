import asyncio

async def g(x,y):
    print(x*y)


async def test(xl,yl):
  await asyncio.gather( *(g(xl[i],yl[i]) for i in range(0,len(xl))) )


xl=(1,2,3)
yl=(1,2,3)
asyncio.run(test(xl,yl))


