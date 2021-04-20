from modules import modules
from adder_graph import adder_graph as graph
from adder_graph import adder_node as node

# Class that generates parallel prefix adder trees

# Trees are initialized to a serial structures (ripple-carry-like)
# Trees can morph via any of three, reversible, transforms:
# L->F, F->L, L->T, T->L, F->T, T->F

# L <-> F was discussed in
# R. Zimmermann, Binary Adder Architectures for Cell-Based VLSI and their Synthesis, PhD thesis, Swiss Federal Institute of Technology (ETH) Zurich, Hartung-Gorre Verlag, 1998
#  J. P. Fishburn. A depth-decreasing heuristic for combinational logic; or how to convert a ripple-carry adder into a carrylookahead adder or anything in-between. In Proc. 27th Design Automation Conf., pages 361–364, 1990

class adder_tree(graph):

    # Pre-condition: width is an integer
    # Post-condition: initializes serial structure

    def __init__(self,width):
        if not isinstance(width,int):
            raise TypeError("provided width must be an integer")

        super().__init__(width)

        # Initialize P/G nodes:
        for a in range(self.w):
            self.add_node(node(a,0,'pg_node'))

        # Initialize serial structure

        for a in range(1,self.w):
            for b in range(self.w):
                if b!=a:
                    self.add_node(node(b,a,'buffer_node'))
                else:
                    self.add_node(node(b,a,'black'),pre=self[b-1,a-1])

        # Post-processing (in progress)

        for a in range(self.w):
            self.add_node(node(a,self.w,'xor_node'))

    # Pre-condition: n is a valid new node; pre is either None or a node in the graph
    # Post-condition: adds node into graph and connects it correctly

    def add_node(self,n,pre=None):

        if pre is not None and not isinstance(pre,node):
            raise TypeError("provided predecessor node must be a node")

        super().add_node(n)
        self._add_top(n)
        self._add_pre(n,pre=pre)

        if self.bot(n) is not None:
            self._add_top(self.bot(n))

    # Internal helper function to prevent re-writing of code
    # Connects node to its upper neighbor

    def _add_top(self,n,pre=None):

        if 'pin' in n.ins:
            pos=len(n.ins['pin'])-1
            self.add_edge(self.top(n),('pout',0),n,('pin',pos))
        if 'gin' in n.ins:
            pos=len(n.ins['gin'])-1
            self.add_edge(self.top(n),('gout',0),n,('gin',pos))

    # Internal helper function to prevent re-writing of code
    # Connects node to a predecessor

    def _add_pre(self,n,pre=None):
        if pre is None:
            return

        if 'pin' in n.ins and len(n.ins['pin'])>1:
            self.add_edge(pre,('pout',0),n,('pin',0))
        if 'gin' in n.ins and len(n.ins['pin'])>1:
            self.add_edge(pre,('gout',0),n,('gin',0))

    # Pre-condition: n is a node in the graph; its intended destination is a buffer
    # Post-condition: n shifts to its intended destination with its full connections
    # n's original location now contains a buffer

    def shift_node(self,n,fun=None):

        if fun==None:
            fun=self.top

        # Grab the buffer we're swapping with
        buf=fun(n)

        if n not in self:
            raise ValueError("trying to shift a node not in the graph")
        if node._exists(buf):
            raise ValueError("can only shift node into buffers")
        if self.pre(n) is not None and self.pre(n).y>=buf.y:
            raise ValueError("cannot shift node past predecessor")
        for x in self.post(n):
            if x.y<=buf.y:
                raise ValueError("cannot shift node past successor")

        # Save pre/post
        pre = self.pre(n)
        post = self.post(n)

        # Remove nodes from graph
        self.remove_node(n)
        self.remove_node(buf)

        # Re-label x/y of nodes
        tmp = n.x; n.x = buf.x; buf.x = tmp; del tmp;
        tmp = n.y; n.y = buf.y; buf.y = tmp; del tmp;

        # Clean edge info (should be re-written to use remove_edge)
        buf.ins={x:[None]*len(buf.ins[x]) for x in buf.ins}
        buf.outs={x:[None]*len(buf.outs[x]) for x in buf.outs}
        n.ins={x:[None]*len(n.ins[x]) for x in n.ins}
        n.outs={x:[None]*len(n.outs[x]) for x in n.outs}

        # Re-add nodes into graph
        if buf.y>n.y:
            self.add_node(n,pre=pre)
            self.add_node(buf)
        else:
            self.add_node(buf)
            self.add_node(n,pre=pre)

        # Re-draw connectons to node
        for x in post:
            self._add_pre(x,pre=n)

        return n

    # Pre-condition: n is a valid node in the main part of the tree (gray/black/buffer)
    # Post-condition: returns the y-1 neighbor (P/G logic if already at the top)

    def top(self,n):
        if n.y==0:
            return None
        return self[n.x,n.y-1]

    # Pre-condition: n is a valid node in the main part of the tree (gray/black/buffer)
    # Post-condition: returns the next-highest non-buffer neighbor

    def r_top(self,n):
        return (self.top(n) if self.top(n).m!="buffer_node" else self.r_top(self.top(n)))

    # Pre-condition: n is a valid node in the main part of the tree (gray/black/buffer)
    # Post-condition: returns the y+1 neighbor (post-processing logic if already at the bot)

    def bot(self,n):
        if n.y+1==len(self.node_list):
            return None
        return self[n.x,n.y+1]

    # Pre-condition: n is a valid node in the main part of the tree (gray/black/buffer)
    # Post-condition: returns the next-lowest non-buffer neighbor

    def r_bot(self,n):
        return (self.bot(n) if self.bot(n).m!="buffer_node" else self.r_bot(self.bot(n)))

    # Pre-condition: n is a valid node in the main part of the tree (gray/black/buffer)
    # Post-condition: returns the diagonal predecessor (None if this node is a buffer)

    def pre(self,n):
        return next(iter([a for a in self.adj[n] if a.x<n.x and a.y<n.y]),None)

    # Pre-condition: n is a valid node in the main part of the tree (gray/black/buffer)
    # Post-condition: returns the list of diagonal successors

    def post(self,n):
        return [a for a in self.adj[n] if a.x>n.x and a.y>n.y]

    # Helper function that checks whether a node is "below" a second node
    # Same column, higher row, or second node straight-up does not exist

    def _is_below(self,n1,n2):
        return (n2 is None) or (n1 is not None and n2.y==n1.y and n2.x>n1.x)

    # Pre-condition: x,y are valid co-ordinates
    # (if y is not provided, searches entire column from bottom-up)
    # Post-condition: checks whether the given x,y node satisfies the transform's
    # initial requirements; if so, returns the two transform pivots

    def _checkLF(self,x,y=None):
        if not isinstance(x,int) or (y is not None and not isinstance(y,int)):
            raise TypeError("x,y values provided to the internal-use-only check function are invalid!")

        # If no y is provided, check whole column from bottom up
        if y is None:
            for a in range(len(self.node_list)-1,-1,-1):
                a,b=self._checkLF(x,a)
                if b is not None:
                    return a,b
            return (None,None)

        # Main clause of the function
        a = self[x,y]
        # ∃ b = pre(a)
        b = self.pre(a)
        if not node._exists(b):
            return (None,None)
        # ∄ top(a), top(top(a))
        if node._exists(self.top(a)) or node._exists(self.top(self.top(a))):
            return (None,None)
        # ∄ top(b)
        if node._exists(self.top(b)):
            return (None,None)

        return (a,b)

    def _checkFL(self,x,y=None):
        if not isinstance(x,int) or (y is not None and not isinstance(y,int)):
            raise TypeError("x,y values provided to the internal-use-only check function are invalid!")

        # If no y is provided, check whole column from bottom up
        if y is None:
            for a in range(len(self.node_list)-1,-1,-1):
                a,b=self._checkFL(x,a)
                if b is not None:
                    return a,b
            return (None,None)

        # Main clause of the function
        a = self[x,y]
        # ∃ b s.t pre(a)=pre(b),
        b = next(iter([x for x in self.post(a) if x is not a]),None)
        if b is None:
            return (None,None)
        # b is below pre(top(a))
        if not self._is_below(pre(top(a)),b):
            return (None,None)
        # ∄ bot(a) or ∄ pre(a)
        if node._exists(self.bot(a)) and node._exists(self.pre(a)):
            return (None,None)

        return (a,b)

    def _checkTF(self,x,y=None):
        if not isinstance(x,int) or (y is not None and not isinstance(y,int)):
            raise TypeError("x,y values provided to the internal-use-only check function are invalid!")

        # If no y is provided, check whole column from bottom up
        if y is None:
            for a in range(len(self.node_list)-1,-1,-1):
                a,b=self._checkTF(x,a)
                if b is not None:
                    return a,b
            return (None,None)

        # Main clause of the function
        a = self[x,y]

        ### Ugly condition
        # ∃ b s.t pre(a) is below pre(b), r_bot(b).y>=a.y
        b = None; tmp = self.pre(a)
        if tmp is None:
            return (None,None)
        while tmp.y>0:
            tmp = self.top(tmp)
            for x in self.post(tmp):
                if self.r_bot(x).y >= a.y:
                    b=x; break;
        if b is None:
            return (None,None)
        # if r_bot(b).y==a.y, pre(r_bot(a)) is below pre(pre(a)):
        if self.r_bot(b).y==a.y and not self._is_below(self.pre(self.pre(a)),self.pre(r_bot(a))):
            return (None,None)

        return (a,b)

    def _checkFT(self,x,y=None):
        if not isinstance(x,int) or (y is not None and not isinstance(y,int)):
            raise TypeError("x,y values provided to the internal-use-only check function are invalid!")

        # If no y is provided, check whole column from bottom up
        if y is None:
            for a in range(len(self.node_list)-1,-1,-1):
                a,b=self._checkFT(x,a)
                if b is not None:
                    return a,b
            return (None,None)

        # Main clause of the function
        a = self[x,y]
        # ∃ b s.t pre(a)=pre(b),
        b = next(iter([x for x in self.post(a) if x is not a]),None)
        if b is None:
            return (None,None)
        # ∄ top(b)
        if node._exists(self.top(b)):
            return (None,None)

        return (a,b)

    def _checkLT(self,x,y=None):
        if not isinstance(x,int) or (y is not None and not isinstance(y,int)):
            raise TypeError("x,y values provided to the internal-use-only check function are invalid!")

        # If no y is provided, check whole column from bottom up
        if y is None:
            for a in range(len(self.node_list)-1,-1,-1):
                a,b=self._checkLT(x,a)
                if b is not None:
                    return a,b
            return (None,None)

        # Main clause of the function
        a = self[x,y]
        # ∃ b = pre(a)
        b = self.pre(a)
        if not node._exists(b):
            return (None,None)
        # ∄ top(a), top(top(a))
        if node._exists(self.top(a)) or node._exists(self.top(self.top(a))):
            return (None,None)
        # ∄ top(b)
        if node._exists(self.top(b)):
            return (None,None)

        return (a,b)

    def _checkTL(self,x,y=None): 
        if not isinstance(x,int) or (y is not None and not isinstance(y,int)):
            raise TypeError("x,y values provided to the internal-use-only check function are invalid!")

        # If no y is provided, check whole column from bottom up
        if y is None:
            for a in range(len(self.node_list)-1,-1,-1):
                a,b=self._checkTL(x,a)

                if b is not None:
                    return a,b
            return (None,None)

        # Main clause of the function
        a = self[x,y]

        ### Ugly condition
        # ∃ b s.t pre(a) is below pre(b), r_bot(b).y>=a.y
        b = None; tmp = self.pre(a)
        if tmp is None:
            return (None,None)
        while tmp.y>0:
            tmp = self.top(tmp)
            for x in self.post(tmp):
                if self.r_bot(x).y >= a.y:
                    b=x; break;
        if b is None:
            return (None,None)
        # if r_bot(b).y==a.y, pre(r_bot(a)) is below pre(pre(a)):
        if self.r_bot(b).y==a.y and not self._is_below(self.pre(self.pre(a)),self.pre(r_bot(a))):
            return (None,None)
        # ∄ bot(a) or ∄ pre(a)
        if node._exists(self.bot(a)) and node._exists(self.pre(a)):
            return (None,None)

        return (a,b)

    def LF(self,x,y=None):
        a,b = self._checkLF(x,y)
        if b is None:
            return None

        # create c=top(top(a)); pre(c) = top(top(b))
        c=self.top(self.top(a))
        self.remove_node(c)

        c=node(c.x,c.y,'black')
        self.add_node(c,pre=self.top(self.top(b)))

        # pre(a) = pre(b)
        self.remove_edge(a,self.pre(a))
        self.remove_edge(a,self.pre(a))

        self._add_pre(a,self.pre(b))

        # a -> top(a)
        self.shift_node(a, self.top)

        return a,b

    def FL(self,x,y=None):
        #a -> bot(a)
        #del c = top(top(a))
        #pre(a) = b
        pass

    def TF(self,x,y=None):
        #del c = bot(b)
        #b -> bot(b)
        #pre(b) = bot(pre(b))
        pass

    def FT(self,x,y=None):
        pass

    def LT(self,x,y=None):
        #LF, followed by FT
        pass

    def TL(self,x,y=None):
        #TF, followed by FL
        pass

    def compress():
        pass

    def reduce():
        pass
