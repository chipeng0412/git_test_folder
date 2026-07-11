import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-3, 3, 50)
y1 = 2*x + 1
#y2 = x**2
plt.figure()


plt.xlim((-1, 2))
plt.ylim((-2, 3))

new_ticks = np.linspace(-1, 2, 5)
print(new_ticks)
plt.xticks(new_ticks)
plt.yticks([-2, -1.8, -1, 1.22, 3,], 
            [r'$really\ bad$', r'$bad\ \theta$', r'$nomal$', r'$good$', r'$very\ good$'])
#gca = 'get current axis'
ax = plt.gca()
ax.spines['right'].set_color('none')
ax.spines['top'].set_color('none')
ax.xaxis.set_ticks_position('bottom')
ax.yaxis.set_ticks_position('left')
ax.spines['bottom'].set_position(('data', 0))
ax.spines['left'].set_position(('data', 0))

x0 = 1
y0 = 2 * x0 +1

#plt.plot(x, y2, label= 'up')
plt.plot(x, y1, color='red', linewidth = 1.0, linestyle = '--', label ='down')
plt.scatter(x0, y0, s=50, color = 'b')
plt.plot([x0, x0], [y0, 0], 'k--', lw=2.5)
plt.legend(labels = ['aaa','bbb'], loc = 'best')

#method 1
plt.annotate(r'$2x+1=%s$'%y0, xy=(x0, y0),xycoords='data',xytext=(+30, -30), textcoords='offset points',
             fontsize = 16, arrowprops=dict(arrowstyle='->', connectionstyle='arc3, rad=.8'))

plt.text(-1, 1,r'$This\ is\ the\ some\ text.\ \mu\ \sigma_i\ \alpha_t$',
         fontdict={'size':16, 'color':'r'})
plt.show()
