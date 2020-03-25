s = set()
with open('temp') as f:
	for line in f.readlines():
		if "%" in line:
			l = line.split(':')
			s.add(l[0])
print(s)
