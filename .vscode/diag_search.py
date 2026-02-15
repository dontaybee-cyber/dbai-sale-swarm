from googlesearch import search
q = "Solar Panel Installation Colorado Springs"
print('Query:', q)
res = list(search(q, num_results=10, sleep_interval=2))
print('Result count:', len(res))
for i,u in enumerate(res,1):
    print(i, u)
